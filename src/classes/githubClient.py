import requests
import time
from tqdm import tqdm
from yaspin import yaspin
from pprint import pprint


class GitHubClient:
    # BASE_URL of API requests
    BASE_URL = "https://api.github.com"

    # The token belongs to the user to prove that the user is an authenticated GitHub user
    # and the repo can be any repo with some issues inside to query about, we want an authenticated
    # GitHub user to raise the users API request limit from 60p/h to 5000p/h

    # https://github.com/curl/curl would be a full repo, the repo provided
    # below would be in the form curl/curl
    def __init__(self, token: str, repo: str, name: str):
        self.token = token # GitHub token
        self.repo = name + "/" + repo
        # https://docs.github.com/en/rest/users/users?apiVersion=2026-03-10
        # "vnd.github+json" instead of plain "json" since we want GitHub's version of
        # the JSON we want returned since it may miss some useful fields
        self.header = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}"
        } 

    def _get(self, path: str, params: dict = None, retries = 30) -> list | dict: # Endpoints may return list or dict
        # Given a path (any endpoint), request some data about it while defining params that would
        # outline the query string such as page number and reject 2xx status codes
        try:
            # If it takes longer then 10 seconds then it would raise an exception in the
            # RequestException as Timeout is a subclass of RequestException

            # https://api.github.com/repos/curl/curl/issues?page=10&per_page=100&state=all
            # Above has some params such as page=10, per_page and state=all to get open and closed issues
            # We have to use aiohttp since requests is blocking, meaning it cannot be done in parallel

            # Raises RequestException
            res = requests.get(url=path, params=params, headers=self.header);

            # Raises HTTP error
            res.raise_for_status()
            data = res.json()
            link = res.headers.get("link")
            return data, link
   
        except requests.HTTPError as e:
            print("HTTP error occurred", e)
            return [], None
        except requests.RequestException as e:
            if(retries > 0):
                time.sleep(4)
                print(f"Retrying, attempts left: {retries - 1}")
                return self._get(path, params, retries - 1)
            else:
                print("All attempts exhausted")
                print("A request error occurred", e)
            return [], None

    # All because we want to include even resolved issues
    def fetchIssues(self, state: str = "all") -> list[dict]:
        nonPRs = 0
        pbar = tqdm()
        issues = []

        print(f"Fetching issues at {self.BASE_URL + "/repos/" + self.repo}")

        def filterKey(key: str, data: list) -> None:
            nonlocal nonPRs # Allows nonPRs to be visible in this nested function
            for entry in data:
                if key not in entry:
                    comments = []
                    if(entry["comments"] > 0):
                        data, _ = self._get(entry["comments_url"])
                        for x in data:
                            comments.append(x["body"])

                    entry["comments"] = comments                    
                    pprint(entry)
                    issues.append(entry)
                    nonPRs = nonPRs + 1
                    pbar.update(nonPRs)
                        
        # We wanna get the issues of the repo given until we receive an empty page
        # we must skip pull requests and ensure we request 100 pages per request
        # to satisfy GitHub and also sleep briefly between pages to not overload the server
        pagesRemaining = True
        pageNumber = 1
    
        #print(self.BASE_URL + "/repos/" + self.repo + "/issues")
        
        data, link = self._get(path=self.BASE_URL + "/repos/" + self.repo + "/issues", params = {"state": state, "per_page": 100})

        filterKey(key='pull_request', data=data)

        if(link is None or ' rel="next' not in link):
            return issues

        # Splits the node into two, URl and the rel=? and strip out the <> to get the pure URL
        url = link.split(";")[0].strip("<>")

        while(pagesRemaining):
            pageNumber = pageNumber + 1
            data, link = self._get(path=url, params=None)
            #print("Next: ", link.split(";")[0].strip("<>"), "Prev: ", link.split(";")[1].strip("<>"), link.split(";")[2])
            if(link is None or ' rel="next' not in link):
                pagesRemaining = False
                filterKey(key='pull_request', data=data)
                return issues
                
            filterKey(key='pull_request', data=data)     

            url = link.split(";")[0].strip("<>")
        
        return issues
    
    def _graphQL_fetch(self, variables: dict, query: str, retries: int = 30) -> dict:
        try:
            res = requests.post(
                "https://api.github.com/graphql",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"query": query, "variables": variables},
                timeout=10,
            )
        except requests.exceptions.ConnectionError as e:
            if retries > 0:
                time.sleep(4)
                print(f"Retrying, attempts left: {retries - 1}")
                return self.graphQL_fetch(variables, query, retries - 1)
            else:
                print("All attempts exhausted")
                print("A request error occurred", e)
            return {}
            
        return res.json()

    def fetch_duplicate_pairs(self, state: str = "all") -> list[int] | list[int]:
        duplicates = []
        canonicals = []
        def filterDuplicate(keys: tuple, data: list) -> None:
            # Given a keys tuple which is just the filter, find the duplications its canonical issue number
            for entry in data:
                # ID of the current issue
                id = entry['number']
                reason = entry['state_reason']
                if keys[0] not in entry and reason == keys[1]:
                    index = self.repo.split("/")
                     # microsoft/vscode -> microsoft, vscode
                    variables = {"owner": index[0], "repo": index[1], "number": id}

                    # This query is a GraphQL query, this aint a RESTFUL one because it doesn't expose this information
                    # there, the idea is that the query() is like a function that is passing the parameters to
                    # repository and issue, where the repository is indexed via the owner and repo and the issue
                    # is indexed by its ID, we can then get the duplicateOf field which exposes the canonical issue number
                    query = """
                    query($owner: String!, $repo: String!, $number: Int!) {
                        repository(owner: $owner, name: $repo) {
                            issue(number: $number) {
                                duplicateOf {
                                    number
                                }
                            }
                        }
                    }
                    """

                    canonicalID = self._graphQL_fetch(variables, query)["data"]["repository"]["issue"]["duplicateOf"]["number"]
                    duplicates.append(id)
                    canonicals.append(canonicalID)

        pagesRemaining = True
        pageNumber = 1
        
        data, link = self._get(path=self.BASE_URL + "/repos/" + self.repo + "/issues", params= {"state": state, "per_page": 100}) 

        filterDuplicate(keys=('pull_request', 'duplicate'), data=data)

        if link is None or ' rel=next' not in link:
            pass

        url = link.split(";")[0].strip("<>")
        
        while(pagesRemaining):
            pageNumber = pageNumber + 1
            data, link = self._get(path=url, params=None)

            if(link is None or ' rel="next' not in link):
                pagesRemaining = False
                filterDuplicate(keys=('pull_request', 'duplicate'), data=data)
            
                return duplicates, canonicals

            filterDuplicate(keys=('pull_request', 'duplicate'), data=data)     

            url = link.split(";")[0].strip("<>")

    # https://api.github.com/repos/OWNER/REPO/contents/PATH
    def get_file(self, path: str):
        url = self.BASE_URL + "/repos/" + self.repo + "/contents/" + path
        data, link = self._get(path=url, params=None)
        return data

    """
    def get_issue_templates(self):
        url = self.BASE_URL + "/repos/" + self.repo + "/contents/" + ".github/ISSUE_TEMPLATE/"
        print(url)
        pass
    def TEMP_get_issue_content(self, path: str):
        url = self.BASE_URL + "/repos/" + self.repo + "/issues/" + path
        data, link = self._get(path=url, params=None)

        return data
    """
