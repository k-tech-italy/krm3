# How to bump a new BE version

!!! warning

    Given the automatic bumping performed by the release pipeline this guide is deprecated and we should never bump manually a release with `cz bump`. see [here](/wiki/ReleaseWorkflow/) for details.

Bumping a new version allows you to publish a new Docker image in the Packages section of GitHub. To publish a new
version, you must run the make bump command in the branch you intend to publish and then merge the branch into the develop branch.
Running the make bump command automatically bumps and create changelog without a need to specify type of change because
it is based on commit names that we created (For example feature tag will result in minor change and fix will result in patch)

```
cz bump
bump: version 1.5.32 → 1.5.33
tag to create: 1.5.33
increment detected: PATCH

```
When bumping, `CHANGELOG.md` is generated automatically. It includes all commits that have correct format which is `type(optional:scope): description`.
If you want to know more about how to correctly create commits click [here](commit.md)

```
## 1.5.32 (2025-09-09)

### Feat

- add commitizen setup

### Fix

- update bump command with interactive mode
```

Anytime a bump is performed, a git `tag` is also generated, is important to push such tag in the remote origin, you can do it manually or set up a configuration to have the tags automatically pushed upon normal push:

### Git Configuration for Automatic Tag Push to GitHub
In the configuration file in `~/.gitconfig`, you can add the following configuration to automatically push both local branches and tags to the remote origin when you run git push.

```
[remote "origin"]
    url = <git_repo>
    push = +refs/heads/*:refs/heads/*
    push = +refs/tags/*:refs/tags/*
```

+ forces the push even in case of discrepancies.
+ refs/heads/* corresponds to branches.
+ refs/tags/* corresponds to tags.

### Command to Push Tags Manually
If you prefer not to change the configuration, or only want to push tags occasionally, you can use this command:

```
git push --tags
```

This command pushes all local tags that are not yet present on the remote.



Once the branch containing the bump is merged into develop with the new version, the build pipeline will publish the Docker image associated with this new version.

The list of published images is available [here](https://github.com/k-tech-italy/krm3/pkgs/container/krm3) whereas the changelog of the released version can be found [here](https://github.com/k-tech-italy/krm3/blob/develop/CHANGELOG.md)
