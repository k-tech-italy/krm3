# # How to bump a new BE version

Bumping a new version allows you to publish a new Docker image in the Packages section of GitHub. To publish a new version, you must run the make bump command in the branch you intend to publish and then merge the branch into the develop branch. Running the make bump command prompts you for the release type (major/minor/patch). The choice depends on the type of change you intend to publish, as shown in the following image:

```
$ make bump
Select version increment:
1) MAJOR
2) MINOR
3) PATCH
Enter choice (1-3):
```
Once the bump type is selected, the commit and tag with new version will be created:

```
bump: version 1.5.32 → 1.5.33
tag to create: 1.5.33
increment detected: PATCH

```
When bumping, `CHANGELOG.md` is generated automatically. It includes all commits that have correct format which is `type(optional:scope): description`
```
## 1.5.32 (2025-09-09)

### Feat

- add commitizen setup

### Fix

- update bump command with interactive mode
```
Once the branch containing the bump is merged into develop with the new version, the build pipeline will publish the Docker image associated with this new version.

The list of published images is available [here](https://github.com/k-tech-italy/krm3/pkgs/container/krm3) whereas the changelog of the released version can be found [here](https://github.com/k-tech-italy/krm3/blob/develop/CHANGELOG.md)
