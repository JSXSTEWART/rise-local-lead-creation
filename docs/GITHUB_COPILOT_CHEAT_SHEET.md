# GitHub Copilot Chat Cheat Sheet

Use this cheat sheet to quickly reference the most common commands and options for using GitHub Copilot Chat.

## Tool Navigation
- Visual Studio Code
- JetBrains IDEs
- Visual Studio
- Web browser
- Xcode

## About GitHub Copilot Enhancements

You can enhance your experience of Copilot Chat with a variety of commands and options. Finding the right command or option for the task you are working on can help you achieve your goals more efficiently. This cheat sheet provides a quick reference to the most common commands and options for using Copilot Chat.

For information about how to get started with Copilot Chat in the GitHub website, see [Asking GitHub Copilot questions in GitHub](https://docs.github.com/en/copilot/using-github-copilot/asking-github-copilot-questions-in-github).

## Mentions

Use `@` mentions to attach relevant context directly to your conversations. Type `@` in the chat prompt box to display a list of items you can attach, such as:

- **Discussions**
- **Extensions**
- **Files**
- **Issues**
- **Pull requests**
- **Repositories**

## Slash Commands

Use slash commands to avoid writing complex prompts for common scenarios. To use a slash command, type `/` in the chat prompt box, followed by the command name.

Available slash commands may vary, depending on your environment and the context of your chat. To view a list of currently available slash commands, type `/` in the chat prompt box of your current environment. Below is a list of some of the most common slash commands for using Copilot Chat.

| Command | Description |
|---------|-------------|
| `/clear` | Clear conversation. |
| `/delete` | Delete a conversation. |
| `/new` | Start a new conversation |
| `/rename` | Rename a conversation. |

## MCP Skills

Below is a list of the MCP skills that are currently available in Copilot Chat in GitHub, and example prompts you can use to invoke them. You do not need to use the MCP skill name in your prompt; you can simply ask Copilot Chat to perform the task.

| Skill | Example Prompt |
|-------|----------------|
| `create_branch` | Create a new branch called [BRANCH-NAME] in the repository [USERNAME/REPO-NAME]. |
| `create_or_update_file` | Add a new file named hello-world.md to my [BRANCH-NAME] of [USERNAME/REPO-NAME] with the content: "Hello, world! This file was created from Copilot Chat in GitHub!" |
| `push_files` | Push the files test.md with the content "This is a test file" and test-again.md with the content "This is another test file" to the [BRANCH-NAME] in [USERNAME/REPO-NAME] |
| `update_pull_request_branch` | Update the branch for pull request [PR-number] in [USERNAME/REPO-NAME] with the latest changes from the base branch. |
| `merge_pull_request` | Merge pull request [PR-Number] in [USERNAME/REPO-NAME] |
| `get_me` | Tell me about myself. |
| `search_users` | Search for users with the name "Mona Octocat" |

## Additional Resources

For more information about GitHub Copilot, see:
- [GitHub Copilot Documentation](https://docs.github.com/en/copilot)
- [GitHub Copilot Chat Documentation](https://docs.github.com/en/copilot/github-copilot-chat)
