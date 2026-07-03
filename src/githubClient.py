import requests
import time
from yaspin import yaspin

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

    def filterKey(self, key: str, data: list, store: list) -> list | int:
        count = 0
        for entry in data:
            if key not in entry:
                store.append(entry)
            else:
                count = count + 1

        return store, count

    def fetchIssues(self, state: str = "all") -> list[dict]:
        # We wanna get the issues of the repo given until we receive an empty page
        # we must skip pull requests and ensure we request 100 pages per request
        # to satisfy GitHub and also sleep briefly between pages to not overload the server
        pagesRemaining = True
        issues = []
        pageNumber = 1
        #print(self.BASE_URL + "/repos/" + self.repo + "/issues")
        with yaspin(text="Loading GitHub issues", color="cyan") as sp:
            sp.write(f"> Loading page {pageNumber}.")
            data, link = self._get(path=self.BASE_URL + "/repos/" + self.repo + "/issues", params = {"state": state, "per_page": 100})
            
            for entry in data:
                if 'pull_request' not in entry:
                    issues.append(entry)

            if(link is None or ' rel="next' not in link):
                return issues

            # Splits the node into two, URl and the rel=? and strip out the <> to get the pure URL
            url = link.split(";")[0].strip("<>")

            while(pagesRemaining):
                pageNumber = pageNumber + 1
                sp.write(f"> Loading page {pageNumber}.")
                data, link = self._get(path=url, params=None)
                #print("Next: ", link.split(";")[0].strip("<>"), "Prev: ", link.split(";")[1].strip("<>"), link.split(";")[2])
                if(link is None or ' rel="next' not in link):
                    pagesRemaining = False
                    issues, count = self.filterKey('pull_request', data, issues)
                    return issues
                
                issues, count = self.filterKey('pull_request', data, issues)     

                url = link.split(";")[0].strip("<>")

            sp.ok("Finished.")
        
        
        return issues
