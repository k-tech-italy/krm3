# # How to bump a new BE version

Bumping a new version allows you to publish a new Docker image in the Packages section of GitHub. To publish a new version, you must run the make bump command in the branch you intend to publish and then merge the branch into the develop branch. Running the make bump command prompts you for the release type (major/minor/release). The choice depends on the type of change you intend to publish, as shown in the following image:

```
$ make bump
bumpversion [major/minor/patch]:
```
Once the bump type is selected, the new version will be printed on the screen:

```
version = "1.5.31"
```
The new version must also be inserted into the changelog file located in the `src/krm3/releases.json` file
along with information about the change you want to publish (whether it's a bug or a feature, and any release notes) as in the following example:

```
{
    "v1.5.31 - 2025-09-03": {
    "features": [
      "issue #280 Add logout button in the /be/ section"
    ],
    "fixes": [
    ],
    "release_notes": [
      "aligned FE submodule to v1.0.25"
    ]
  }
}
```
Once the changelog file is updated, add all the files modified by the make bump command, create a commit including the new version in the commit message, and push the commit. Once the branch containing the bump is merged into develop with the new version, the build pipeline will publish the Docker image associated with this new version.

The list of published images is available [here](https://github.com/k-tech-italy/krm3/pkgs/container/krm3) whereas the changelog of the released version can be found [here](https://krm3.k-tech.it/be/releases/)
