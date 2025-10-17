🧭 Build & Deploy Workflow Guide

⚙️ 1️⃣ — Development on the develop branch

All work starts from the develop branch.

Create a new feature or fix branch:

Stage the files:

git add .

Commit using Commitizen:

cz commit


You’ll be prompted to choose the type of change:

fix: → bug fix → patch bump (e.g. 1.9.7 → 1.9.8)

feat: → new feature → minor bump (e.g. 1.9 → 1.10)

BREAKING CHANGE: → major change → major bump (e.g. 1.x → 2.0)

💡 Commitizen ensures all commit messages follow the Conventional Commits standard.

Push your branch

------------------------------------

🧪 2️⃣ — Automatic tests on develop

Once merged into develop, the test pipeline runs automatically.

🔍 Trigger condition:
The test pipeline is triggered only if something has changed in:

src/

tests/


If all tests pass ✅, the develop branch is ready for a new build and deployment.

-----------------------------------------


🚀 3️⃣ — Manual Build & Deploy

When you’re ready to release a new version:

Go to GitHub Actions

Find the workflow named “Build and Deploy”

Select the develop branch

Click “Run workflow”

------------------------------------------------------------------

 **What this pipeline does**

🧩 Step 1 — Version bump

Runs cz bump to update version numbers (__init__.py, pyproject.toml, etc.)

Creates a new tag (e.g. v1.9.8)

Pushes the commit and tag to develop

Merges the latest develop changes into master

🏗️ Step 2 — Build

Builds the Python package using uv build

Compiles the frontend (krm3-fe)

Generates release.json

Builds the Docker image

📦 Step 3 — Push

Pushes the Docker image to GitHub Container Registry (ghcr.io)
→ e.g. ghcr.io/your-org/krm3:1.9.8 and ghcr.io/your-org/krm3:latest

☸️ Step 4 — Deploy to Kubernetes

Calls the Rancher API using RANCHER_URL and RANCHER_TOKEN

Updates the deployment with the new Docker image

Waits for manual approval in the production environment

👩‍💼 Step 5 — Manual approval

An administrator must approve the deployment in
GitHub → Environments → production

Once approved, the workflow performs the final redeploy on Kubernetes
