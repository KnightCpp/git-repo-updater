# -*- coding: utf-8  -*-
#
# Copyright (C) 2011-2014 Ben Kurtovic <ben.kurtovic@gmail.com>
# See the LICENSE file for details.

import os
import shlex
import subprocess

from .output import out, bold, red, green, blue

__all__ = ["update_bookmarks", "update_directories"]

def _exec_shell(command):
    """Execute a shell command and get the output."""
    command = shlex.split(command)
    result = subprocess.check_output(command, stderr=subprocess.STDOUT)
    if result:
        result = result[:-1]  # Strip newline if command returned anything
    return result

def _directory_is_git_repo(directory_path):
    """Check if a directory is a git repository."""
    if os.path.isdir(directory_path):
        git_subfolder = os.path.join(directory_path, ".git")
        if os.path.isdir(git_subfolder):  # Check for path/to/repository/.git
            return True
    return False

def _update_repository(repo_path, repo_name):
    """Update a single git repository by pulling from the remote."""
    out(1, bold(repo_name) + ":")

    # cd into our folder so git commands target the correct repo:
    os.chdir(repo_path)

    try:
        # Check if there is anything to pull, but don't do it yet:
        dry_fetch = _exec_shell("git fetch --dry-run")
    except subprocess.CalledProcessError:
        out(2, red("Error: ") + "cannot fetch; do you have a remote " \
            "repository configured correctly?")
        return

    try:
        last_commit = _exec_shell("git log -n 1 --pretty=\"%ar\"")
    except subprocess.CalledProcessError:
        last_commit = "never"  # Couldn't get a log, so no commits

    if not dry_fetch:  # No new changes to pull
        out(2, blue("No new changes.") +
            " Last commit was {0}.".format(last_commit))

    else:  # Stuff has happened!
        out(2, "There are new changes upstream...")
        status = _exec_shell("git status")

        if status.endswith("nothing to commit, working directory clean"):
            out(2, green("Pulling new changes..."))
            result = _exec_shell("git pull")
            out(2, "The following changes have been made since {0}:".format(
                    last_commit))
            print(result)

        else:
            out(2, red("Warning: ") +
                "you have uncommitted changes in this repository!")
            out(2, "Ignoring.")

def _update_directory(dir_path, dir_name, is_bookmark=False):
    """Update a particular directory.

    First, make sure the specified object is actually a directory, then
    determine whether the directory is a git repo on its own or a directory
    of git repositories. If the former, update the single repository; if the
    latter, update all repositories contained within.
    """
    if is_bookmark:
        dir_type = "bookmark"  # Where did we get this directory from?
    else:
        dir_type = "directory"

    dir_long_name = "{0} '{1}'".format(dir_type, bold(dir_path))

    try:
        os.listdir(dir_path)  # Test if we can access this directory
    except OSError:
        out(0, red("Error: ") +
            "cannot enter {0}; does it exist?".format(dir_long_name))
        return

    if not os.path.isdir(dir_path):
        if os.path.exists(dir_path):
            out(0, red("Error: ") + dir_long_name + " is not a directory!")
        else:
            out(0, red("Error: ") + dir_long_name + " does not exist!")
        return

    if _directory_is_git_repo(dir_path):
        out(0, dir_long_name.capitalize() + " is a git repository:")
        _update_repository(dir_path, dir_name)

    else:
        repositories = []

        dir_contents = os.listdir(dir_path)  # Get potential repos in directory
        for item in dir_contents:
            repo_path = os.path.join(dir_path, item)
            repo_name = os.path.join(dir_name, item)
            if _directory_is_git_repo(repo_path):  # Filter out non-repositories
                repositories.append((repo_path, repo_name))

        num_of_repos = len(repositories)
        if num_of_repos == 1:
            out(0, dir_long_name.capitalize() + " contains 1 git repository:")
        else:
            out(0, dir_long_name.capitalize() +
                " contains {0} git repositories:".format(num_of_repos))

        repositories.sort()  # Go alphabetically instead of randomly
        for repo_path, repo_name in repositories:
            _update_repository(repo_path, repo_name)

def update_bookmarks(bookmarks):
    """Loop through and update all bookmarks."""
    if bookmarks:
        for bookmark_path, bookmark_name in bookmarks:
            _update_directory(bookmark_path, bookmark_name, is_bookmark=True)
    else:
        out(0, "You don't have any bookmarks configured! " \
            "Get help with 'gitup -h'.")

def update_directories(paths):
    """Update a list of directories supplied by command arguments."""
    for path in paths:
        path = os.path.abspath(path)  # Convert relative to absolute path
        path_name = os.path.split(path)[1]  # Dir name ("x" in /path/to/x/)
        _update_directory(path, path_name, is_bookmark=False)
