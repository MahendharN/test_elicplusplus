import os
from github import Github
import subprocess
from git import Repo
import git

GITHUB_EVENT_NAME = 'GITHUB_EVENT_NAME'
GITHUB_SHA = 'GITHUB_SHA'
GITHUB_REF = 'GITHUB_REF'
GITHUB_HEAD_REF = 'GITHUB_HEAD_REF'
GITHUB_BASE_REF = 'GITHUB_BASE_REF'
GITHUB_REPOSITORY = 'GITHUB_REPOSITORY'
GITHUB_MAJOR_PR_NUMBER = "pr_number"
GITHUB_TOKEN = 'GITHUB_TOKEN'


MAX_MAJOR_VERSION = 5
MAX_RC_BRANCH_FIND_RETRY = 10
def get_pr_info():
    # Get information about the pull request from environment variables
    github_event_name = os.environ.get(GITHUB_EVENT_NAME)
    github_ref = os.environ.get(GITHUB_REF)
    github_head_ref = os.environ.get(GITHUB_HEAD_REF)
    github_base_ref = os.environ.get(GITHUB_BASE_REF)
    github_repository = os.environ.get(GITHUB_REPOSITORY)
    github_token = os.environ.get(GITHUB_TOKEN)

    # Extract PR number from the ref
    try:
        pr_number = github_ref.split('/')[-2] if github_ref else None
    except Exception as e:
        print(f"Exception while getting PR number {e}")
        exit(0)

    return {
        GITHUB_EVENT_NAME: github_event_name,
        GITHUB_REF: github_ref,
        GITHUB_HEAD_REF: github_head_ref,
        GITHUB_BASE_REF: github_base_ref,
        GITHUB_REPOSITORY: github_repository,
        GITHUB_MAJOR_PR_NUMBER: pr_number,
        GITHUB_TOKEN: github_token
    }

def run_git_command(command):
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,  # Ensure the output is in text mode
            check=True   # Raise an exception for non-zero return codes
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        # Handle the error (e.stderr contains the error message)
        print(f"Error running command: {e.stderr}")
        return None
    
class RCUpdate():
    def __init__(self):
        self.pr_info = get_pr_info()
        self.gitub = Github(self.pr_info.get(GITHUB_TOKEN))
        self.repo = Repo(".")
        self.repo.git.config("user.name", "github-actions")
        self.repo.git.config("user.email", "github-actions@github.com")
        self.gh_repo = self.gitub.get_repo(self.pr_info.get(GITHUB_REPOSITORY))
        print(self.gh_repo.get_branch("rc_5.24.0"))
        try:
            self.mj_major_version = int(self.pr_info.get(GITHUB_BASE_REF).split("-")[-1].split(".")[0])
            self.mj_minor_version = int(self.pr_info.get(GITHUB_BASE_REF).split("-")[-1].split(".")[1])
        except Exception as e:
            print(f"Exception while getting vyuha version from branch name. Exception {e}. Improper branch name. Branch Name {self.pr_info[GITHUB_BASE_REF]}")
            exit(0)
        self.rc_branch_name = self.get_rc_branch()
        if self.rc_branch_name == None:
            print("No RC Branch . Thus exiting")
            exit(0)
        if self.pr_info.get(GITHUB_HEAD_REF,"") == "":
            print("No HEAD BRANCH . Thus exiting")
            exit(0)
        self.process()

    def get_rc_branch(self):
        for i in range(1,MAX_RC_BRANCH_FIND_RETRY):
            branch_name = f"rc_{self.mj_major_version}.{self.mj_minor_version+i}.0"
            print(branch_name)
            if self.check_if_branch_is_present(branch_name):
                return branch_name
        return None

    def check_if_branch_is_present(self,branch_name):      
        print(self.repo.heads)  
        try:
            self.gh_repo.get_branch(branch_name)
            return True
        except:
            return False
        
    def push_branch(self,branch_name):
        try:
            self.repo.git.push("origin",branch_name)
        except Exception as e:
            print(f"Exception while pushing branch {branch_name} . Exception {e}")
            exit()


    def check_if_rc_head_is_present(self):
        self.head_rc_branch = f"{self.rc_branch_name}-{self.pr_info.get(GITHUB_HEAD_REF)}"
        if self.check_if_branch_is_present(f"{self.rc_branch_name}-{self.pr_info.get(GITHUB_HEAD_REF)}") == False:
            return False
        return True
    
    def create_pr(self):
        self.create_new_branch(self.head_rc_branch,self.pr_info.get(GITHUB_HEAD_REF))
        self.push_branch(self.head_rc_branch)
        self.create_pull_request(f"{self.pr_info.get(GITHUB_HEAD_REF)} Branch Rebase to RC",self.head_rc_branch,self.rc_branch_name,"")

    def create_new_branch(self, new_branch_name, base_branch):
        # Get the base branch
        try:
            self.repo.create_head(new_branch_name, commit=f'origin/{base_branch}')
            print(f"New branch '{new_branch_name}' created successfully from '{base_branch}'.")
        except Exception as e:
            print("Exception while creating branch {new_branch_name}. Exception {e}. Exiting..")
            exit()


    def create_pull_request(self, title, head_branch, base_branch, body=''):
        try:
            pull_request = self.gh_repo.create_pull(
                title=title,
                body=body,
                base=base_branch,
                head=head_branch
            )
            print(f"Pull request #{pull_request.number} created successfully.")
            return pull_request
        except Exception as e:
            print(f"Error creating pull request: {e}")
            exit()

    def is_pull_request_present(self, base_branch, head_branch):
        pull_requests = self.gh_repo.get_pulls(base=base_branch, head=head_branch, state='open')

        return any(pull_request for pull_request in pull_requests)

    def update_pr(self):
        try:
            self.repo.git.checkout(self.head_rc_branch)
            self.repo.git.pull('origin', self.pr_info.get(GITHUB_HEAD_REF))
            self.push_branch(self.head_rc_branch)
        except Exception as e:
            print(f"Exception while updating to RC-head branch {self.head_rc_branch}. Exception {e}")
            exit()
        if self.is_pull_request_present(self.rc_branch_name,self.head_rc_branch):
            print("Updated RC HEad branch as PR is already present")
        else:
            self.create_pull_request(f"{self.pr_info.get(GITHUB_HEAD_REF)} Branch Rebase to RC",self.head_rc_branch,self.rc_branch_name,"")
        
  
    def process(self):
        if self.check_if_rc_head_is_present():
            self.update_pr()
        else:
            self.create_pr()



if __name__ == '__main__':
    rcupdate = RCUpdate()
    pr_branch = os.getenv('PR_BRANCH')



