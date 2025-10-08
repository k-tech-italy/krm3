# # How to bump a new BE version

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
Once the branch containing the bump is merged into develop with the new version, the build pipeline will publish the Docker image associated with this new version.

The list of published images is available [here](https://github.com/k-tech-italy/krm3/pkgs/container/krm3) whereas the changelog of the released version can be found [here](https://github.com/k-tech-italy/krm3/blob/develop/CHANGELOG.md)
