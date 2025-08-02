# Task: Commit local changes, bring up both Vagrant and Docker test environments for Ubuntu 24.04, and ensure self-healing provisioning.

You are the `env-verifier` CLI agent.

## Instructions:

### 1. Pre-Flight Commit

- Ensure git working tree is clean:

```bash
git add . && git commit -m "chore: save pre-test changes"
```

- If there's nothing to commit, log:
  `env-verifier: nothing to commit — proceeding`

### 2. Vagrant Test

```bash
vagrant up --provider=virtualbox
```

- If exit code = 0:
  - SSH test:

    ```bash
    vagrant ssh -c "uname -r && echo env-verifier: Vagrant Ubuntu‑24.04 up"
    ```

  - On success: log that Vagrant test passed.

- If failure:
  - Grab last 200 lines of stderr.
  - If failure contains known string about building guest additions or missing
    kernel headers:
    - Insert or update provisioning script to `sudo apt update` and
      `sudo apt install -y build-essential dkms linux-headers-$(uname -r)`
    - Commit with message:

      ```
      fix: install prerequisites for Guest Additions (build‑essential, dkms, linux‑headers)
      ```

    - Re-run `vagrant up` once.
    - Re-check SSH connectivity.

  - If the base box is unavailable or reported missing ("cannot find box for
    ubuntu‑24‑04"):
    - Update `Vagrantfile` to use:

      ```ruby
      config.vm.box = "hashicorp-education/ubuntu-24-04"
      ```

    - Commit with message:

      ```
      feat: switch to hashicorp‑education/ubuntu‑24‑04 box
      ```

    - Rerun `vagrant up` and test SSH again.

### 3. Docker Test

- Ensure Docker and `docker-compose` are available.
- Bring up:

```bash
docker-compose -f docker-compose.smoketest.yml up -d
```

- On failure:
  - Check logs:

    ```bash
    docker logs dev-box-smoke-test
    ```

  - If critical missing packages (`build-essential`, `linux-headers`):
    - Add to `Dockerfile` or `docker-compose` provisioning section:

      ```
      RUN apt update && apt install -y build-essential dkms linux-headers-$(uname -r)
      ```

    - Commit with message:

      ```
      fix: add required build tools for Docker Ubuntu 24.04 image
      ```

    - Rerun smoke test.

- On success:

  ```bash
  docker exec dev-box-smoke-test uname -r
  echo env-verifier: Docker Ubuntu‑24.04 up
  ```

### 4. Final Status Log

Once both tests pass (or if Docker isn't applicable):

```
env-verifier: smoke‑test passed (vagrant: ✅, docker: ✅)
```

### 5. Push Changes

```bash
git push origin HEAD
```

- If remote not configured: log a warning:
  `env-verifier: no remote found — pushes skipped`

---

## 🧩 Behavioral Requirements

- Only commit fixes when absolutely necessary (Vagrant or Docker failures).
- Do not commit intermediary files or logs (`ARG-files.log` should remain
  ignored).
- Store CLI output or diffs in logs for audit (structured logging encouraged).
- Do not halt workflow unless there is user ambiguity (e.g. unclear failure
  output).

---

## 🛠 Allowed Modifications

- Shell provisioners (e.g., `.sh`, `Vagrantfile`, or
  `docker-compose.smoketest.yml`).
- Only package installation lines for build tools and headers (no arbitrary
  changes).

---

## Why This Is Important

- **Ubuntu 24.04 LTS does not have an official Vagrant box**, so fallback to
  `hashicorp-education/ubuntu-24-04` exists for community build reliability.

- **Common provisioning failures in Ubuntu 24.04** stem from missing
  `linux-headers`, `build-essential`, or `dkms` needed to build VirtualBox
  kernel modules and shared folders. Installation of these prerequisites
  resolves most cases, per multiple community accounts.

---

## 🚀 Usage

Save this prompt and invoke with Claude‑Flow:

```bash
npx claude-flow@alpha swarm \
  --template .llmconfig/prompt-templates/commit_and_test_all_providers.md \
  "Verify full Ubuntu 24.04 environment across both providers"
```

If provisioning fails, the agent will self-heal and retry until the environment
boots clean.

Once both environments are verified, you'll see:

```
env-verifier: smoke‑test passed (vagrant: ✅, docker: ✅)
```
