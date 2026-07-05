import requests
import time
from tqdm import tqdm
from yaspin import yaspin
from pprint import pprint

class GitHubClient:
    BASE_URL = "https://api.github.com"

    # The token belongs to the user to prove that the user is an authenticated GitHub user
    # and the repo can be any repo with some issues inside to query about, we want an authenticated
    # GitHub user to raise the users API request limit from 60p/h to 5000p/h

    # https://github.com/curl/curl would be a full repo, the repo provided
    # below would be in the form curl/curl
    def __init__(self, token: str, repo: str):
        self.token = token
        self.repo = repo
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
            res = requests.get(path, headers=self.header, params=params, timeout=20)
            res.raise_for_status()
   
        except requests.exceptions.HTTPError as e:
            print("HTTP error occurred", e)
            return []
        except requests.exceptions.RequestException as e:
            if(retries > 0):
                time.sleep(4)
                print(f"Retrying, attempts left: {retries - 1}")
                return self._get(path, params, retries - 1)
            else:
                print("All attempts exhausted")
                print("A request error occurred", e)
            return []

        # Grab the link header since we 
        return res.json(), res.headers.get('link')

    def fetchIssues(self, state: str = "all") -> list[dict]:
        nonPRs = 0
        print(f"Fetching issues at {self.BASE_URL + "/repos/" + self.repo}")
        pbar = tqdm()
        issues = []

        def filterKey(key: str, data: list) -> None:
            nonlocal nonPRs # Allows nonPRs to be visible in this nested function
            for entry in data:
                if key not in entry:
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

    def fetch_duplicate_pairs(self, state: str = "all") -> list[tuple[int, int]]:
        duplicates = []
        def filterDuplicate(keys: tuple, data: list) -> None:
            # Given a keys tuple which is just the filter, find the duplications its canonical issue number
            for entry in data:
                # ID of the current issue
                id = entry['number']
                reason = entry['state_reason']
                if keys[0] not in entry and reason == keys[1]:
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

                    # microsoft/vscode -> microsoft, vscode
                    index = self.repo.split("/")
                    print(index[0], index[1])

                    variables = {"owner": index[0], "repo": index[1], "number": id}

                    res = requests.post(
                        "https://api.github.com/graphql",
                        headers={"Authorization": f"Bearer {self.token}"},
                        json={"query": query, "variables": variables},
                        timeout=10,
                    )
                    canonical = res.json()["data"]["repository"]["issue"]["duplicateOf"]["number"]
                    duplicates.append((id, canonical))
                    #print(res["data"]["repository"]["issue"].json())
                

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
            
                return duplicates

            filterDuplicate(keys=('pull_request', 'duplicate'), data=data)     

            url = link.split(";")[0].strip("<>")

        pass
