# How to create a commit

With commitizen tool to include commits in an automatically created changelog you need to create commits in a correct
name format which is `type(optional:scope): description`.
With help of commitizen you can run `cz commit` to open interactive commit option.
```
? Select the type of change you are committing (Use arrow keys)
» fix: A bug fix. Correlates with PATCH in SemVer
  feat: A new feature. Correlates with MINOR in SemVer
  docs: Documentation only changes
  style: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)
  refactor: A code change that neither fixes a bug nor adds a feature
  perf: A code change that improves performance
  test: Adding missing or correcting existing tests
  build: Changes that affect the build system or external dependencies (example scopes: pip, docker, npm)
  ci: Changes to CI configuration files and scripts (example scopes: GitLabCI)
? What is the scope of this change? (class or file name): (press [enter] to skip)
? Write a short and imperative summary of the code changes: (lower case and no period)
? Provide additional contextual information about the code changes: (press [enter] to skip)
? Is this a BREAKING CHANGE? Correlates with MAJOR in SemVer (y/N)
? Footer. Information about Breaking Changes and reference issues that this commit closes: (press [enter] to skip)
```

## Typical workflow
When working on a ticket it's not required to commit everytime with `cz commit`. You can create commits without required
commit name format but at the end to include those commits in changelog it's good practice to squash those commits and name the squash commit `type(optional:scope): description`.
If you want to use interactive commit tool you can squash commits and run `git reset --soft HEAD~1` which will reset last commit but will keep changes staged.
After that run `cz commit`.

Based on the choice made during the `cz commit` command, the version will be updated according to the following criteria:

- If `fix` is ​​selected: a `PATCH` version update will be performed during the bump.
- If `feat` is selected: a `MINOR` version update will be performed during the bump.
- If `Y` is selected for the question `Is this a BREAKING CHANGE?` option a MAJOR version update will be performed during the bump.
