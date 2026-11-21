"""bin/roz-forge — the bot credential reaches one child and nothing else (#413).

Dummy credentials only: a throwaway RSA key made here, a fake token, a stub
GitHub API on 127.0.0.1, and fake `gh` / `glab` / `git push` executables that
record their argv and environment. No network, no real credential.

The tool runs as a real process. A small runner loads it as a module only to
point `GITHUB_API` at the stub — the production code has no test switch.
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
TOOL = HOOKS.parent / "bin" / "roz-forge"
TOKEN = "ghs_dummyBotToken0123456789"
HUMAN = "human-credential-must-not-reach-the-child"
RUNNER = r"""
import importlib.machinery, importlib.util, json, os, sys
loader = importlib.machinery.SourceFileLoader("roz_forge", sys.argv[1])
spec = importlib.util.spec_from_loader("roz_forge", loader)
mod = importlib.util.module_from_spec(spec)
loader.exec_module(mod)
mod.GITHUB_API = sys.argv[2]
rc = mod.main(sys.argv[4:])
with open(sys.argv[3], "w") as f:
    json.dump(dict(os.environ), f)
sys.exit(rc)
"""
FAKE = r"""#!%s
import json, os, sys
with open(os.environ["FAKE_LOG"], "a") as f:
    conf = os.environ.get("GH_CONFIG_DIR") or os.environ.get("GLAB_CONFIG_DIR") or ""
    f.write(json.dumps({"argv": [os.path.basename(sys.argv[0])] + sys.argv[1:],
                        "env": dict(os.environ),
                        "conf": sorted(os.listdir(conf)) if os.path.isdir(conf) else None}) + "\n")
print("fake %%s ran" %% os.path.basename(sys.argv[0]))
"""
# a person's stored CLI logins, which no child may read
STORED = {"GH_CONFIG_DIR": "/human/gh", "GLAB_CONFIG_DIR": "/human/glab"}
# git: the tool's own reads run the real git; only `push` is faked.
FAKE_GIT = r"""#!%s
import json, os, sys
if "push" in sys.argv[1:]:
    with open(os.environ["FAKE_LOG"], "a") as f:
        f.write(json.dumps({"argv": ["git"] + sys.argv[1:], "env": dict(os.environ)}) + "\n")
    sys.exit(0)
os.execv(%r, [%r] + sys.argv[1:])
"""
DIRTY = {  # a human's ambient credentials, all of which the child must lose
    "GH_TOKEN": HUMAN, "GITHUB_TOKEN": HUMAN, "GH_ENTERPRISE_TOKEN": HUMAN,
    "GITHUB_ENTERPRISE_TOKEN": HUMAN, "GH_HOST": "evil.example",
    "GITLAB_TOKEN": HUMAN, "GITLAB_ACCESS_TOKEN": HUMAN, "OAUTH_TOKEN": HUMAN,
    "GITLAB_HOST": "evil.example", "GL_HOST": "evil.example",
    "GIT_ASKPASS": "/bin/echo", "SSH_ASKPASS": "/bin/echo",
    "GIT_CONFIG_PARAMETERS": "'credential.helper=store'",
    "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "credential.helper", "GIT_CONFIG_VALUE_0": "store",
}


class Stub(BaseHTTPRequestHandler):
    """The two GitHub routes a mint calls; `mode` picks the failure."""

    def log_message(self, *a):
        pass

    def answer(self, code, body):
        self.server.calls.append((self.command, self.path, self.headers.get("Authorization", "")))
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        mode = self.server.mode
        if mode == "500":
            return self.answer(500, "{}")
        if mode == "badjson":
            return self.answer(200, "not json")
        return self.answer(200, json.dumps({"id": 7}))

    def do_POST(self):
        mode = self.server.mode
        token = "" if mode == "empty" else TOKEN
        return self.answer(201, json.dumps({"token": token}))


class ForgeTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.home = self.tmp / "home"
        (self.home / ".config" / "roz-gate").mkdir(parents=True)
        self.log = self.tmp / "fake.log"
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        real_git = subprocess.run(["which", "git"], capture_output=True, text=True).stdout.strip()
        for name in ("gh", "glab"):
            self.exe(name, FAKE % sys.executable)
        self.exe("git", FAKE_GIT % (sys.executable, real_git, real_git))
        self.server = HTTPServer(("127.0.0.1", 0), Stub)
        self.server.mode, self.server.calls = "ok", []
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.key = self.home / ".config" / "roz-gate" / "roz-bot.pem"
        subprocess.run(["openssl", "genrsa", "-out", str(self.key), "2048"],
                       capture_output=True, check=True)
        self.key.chmod(0o600)
        self.repo = self.new_repo("https://github.com/o/r.git",
                                  forge="github", bot_login="roz-bot", bot_app_id="123")

    def exe(self, name, text):
        p = self.bin / name
        p.write_text(text)
        p.chmod(0o755)

    def new_repo(self, url, identity="bot", **keys):
        repo = Path(tempfile.mkdtemp(dir=str(self.tmp)))
        subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", url], check=True)
        block = "".join("- %s: %s\n" % kv for kv in dict(agent_identity=identity, **keys).items())
        (repo / "CLAUDE.md").write_text("### Roz Gate config\n\n" + block)
        return repo

    def run_tool(self, *args, cwd=None, env=None):
        if self.log.exists():
            self.log.unlink()
        after = self.tmp / "after-env.json"
        full = dict(os.environ, HOME=str(self.home), FAKE_LOG=str(self.log),
                    PATH="%s:%s" % (self.bin, os.environ["PATH"]),
                    GIT_CONFIG_GLOBAL=str(self.tmp / "no-global"), GIT_CONFIG_NOSYSTEM="1",
                    **DIRTY, **STORED)
        full.update(env or {})
        p = subprocess.run([sys.executable, "-c", RUNNER, str(TOOL),
                            "http://127.0.0.1:%d" % self.server.server_port, str(after), *args],
                           cwd=str(cwd or self.repo), env=full, capture_output=True, text=True)
        p.after_env = json.loads(after.read_text()) if after.exists() else {}
        return p

    def children(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def assertNoChild(self, p, says):
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertIn(says, p.stderr)
        self.assertIn("no forge call made", p.stderr)
        self.assertEqual(self.children(), [], "a refusal must start no child")
        self.assertNotIn(TOKEN, p.stdout + p.stderr)


class ArgvAndEnv(ForgeTest):
    def test_gh(self):
        p = self.run_tool("gh", "issue", "edit", "5", "--add-label", "track: spec")
        with self.subTest("roz-forge gh: the child runs with the bot token, exit passes through"):
            self.assertEqual(p.returncode, 0, p.stderr)
            (child,) = self.children()
            self.assertEqual(child["argv"],
                             ["gh", "issue", "edit", "5", "--add-label", "track: spec"])
            self.assertEqual(child["env"]["GH_TOKEN"], TOKEN)
        with self.subTest("roz-forge gh: ambient credentials are scrubbed; GH_HOST is github.com"):
            env = child["env"]
            for k in ("GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"):
                self.assertNotIn(k, env)
            self.assertEqual(env["GH_HOST"], "github.com")
            self.assertEqual(env["GH_PROMPT_DISABLED"], "1")
            self.assertNotIn(HUMAN, json.dumps(env))
        with self.subTest("roz-forge gh: the child's gh config is a fresh directory — no stored "
                          "login answers, even for another --hostname (codex review, PR #424)"):
            self.assertNotEqual(env["GH_CONFIG_DIR"], STORED["GH_CONFIG_DIR"])
            self.assertTrue(os.path.basename(env["GH_CONFIG_DIR"]).startswith("roz-forge-cli-"))
            self.assertEqual(child["conf"], [], "an existing, empty directory while gh runs")
            self.assertFalse(os.path.exists(env["GH_CONFIG_DIR"]), "removed after the call")
        with self.subTest("roz-forge gh: the token is in no argv, no tool output, no parent env"):
            self.assertNotIn(TOKEN, json.dumps(child["argv"]))
            self.assertNotIn(TOKEN, p.stdout.replace("fake gh ran", "") + p.stderr)
            self.assertNotIn(TOKEN, json.dumps(p.after_env))
        with self.subTest("roz-forge gh: one installation lookup and one token POST, JWT signed "
                          "by the App key with iss = bot_app_id"):
            calls = self.server.calls
            self.assertEqual([(m, path) for m, path, _ in calls],
                             [("GET", "/repos/o/r/installation"),
                              ("POST", "/app/installations/7/access_tokens")])
            jwt = calls[0][2].split(" ", 1)[1]
            self.assertTrue(self.verifies(jwt))
            payload = jwt.split(".")[1]
            claims = json.loads(self.b64(payload))
            self.assertEqual(claims["iss"], "123")

    def b64(self, s):
        import base64
        return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

    def verifies(self, jwt):
        head, body, sig = jwt.split(".")
        pub = self.tmp / "pub.pem"
        subprocess.run(["openssl", "rsa", "-in", str(self.key), "-pubout", "-out", str(pub)],
                       capture_output=True, check=True)
        (self.tmp / "sig").write_bytes(self.b64(sig))
        return subprocess.run(["openssl", "dgst", "-sha256", "-verify", str(pub), "-signature",
                               str(self.tmp / "sig")], input=("%s.%s" % (head, body)).encode(),
                              capture_output=True).returncode == 0

    def test_glab(self):
        repo = self.new_repo("git@gitlab.example.com:g/p.git", forge="gitlab",
                             bot_login="project_9_bot_x")
        tok = self.home / ".config" / "roz-gate" / "project_9_bot_x.token"
        tok.write_text("glpat-dummy0123\n")
        tok.chmod(0o600)
        p = self.run_tool("glab", "issue", "note", "5", "--message", "hi", cwd=repo)
        with self.subTest("roz-forge glab: the child gets the token file's token and "
                          "origin's host"):
            self.assertEqual(p.returncode, 0, p.stderr)
            (child,) = self.children()
            self.assertEqual(child["env"]["GITLAB_TOKEN"], "glpat-dummy0123")
            self.assertEqual(child["env"]["GITLAB_HOST"], "gitlab.example.com")
        with self.subTest("roz-forge glab: the child's glab config is a fresh directory"):
            self.assertNotEqual(child["env"]["GLAB_CONFIG_DIR"], STORED["GLAB_CONFIG_DIR"])
            self.assertTrue(os.path.basename(child["env"]["GLAB_CONFIG_DIR"])
                            .startswith("roz-forge-cli-"))
        with self.subTest("roz-forge glab: ambient GitLab credentials are scrubbed, no mint call"):
            for k in ("GITLAB_ACCESS_TOKEN", "OAUTH_TOKEN", "GL_HOST"):
                self.assertNotIn(k, child["env"])
            self.assertNotIn(HUMAN, json.dumps(child["env"]))
            self.assertEqual(self.server.calls, [])
            self.assertNotIn("glpat-dummy0123", p.stderr + json.dumps(p.after_env))

    def test_exit_code_passes_through(self):
        self.exe("gh", FAKE % sys.executable + "sys.exit(3)\n")
        with self.subTest("roz-forge gh: the child's exit code is the tool's"):
            self.assertEqual(self.run_tool("gh", "pr", "view", "1").returncode, 3)


class FailClosed(ForgeTest):
    def test_mint_failures(self):
        for mode, says in (("500", "HTTP 500"), ("badjson", "mint failed"),
                           ("empty", "returned no token")):
            self.server.mode, self.server.calls = mode, []
            with self.subTest("roz-forge: mint %s exits 2 and starts no child" % mode):
                self.assertNoChild(self.run_tool("gh", "issue", "list"), says)

    def test_refusals_before_any_call(self):
        def cases():
            yield "a group-readable key", lambda: self.key.chmod(0o640), "readable by others"
            yield "a missing key", lambda: self.key.unlink(), "no credential file"
            yield "a key path that is a directory", lambda: (
                self.key.unlink(), self.key.mkdir()), "not a regular file"
        for name, arrange, says in cases():
            self.setUp()
            arrange()
            with self.subTest("roz-forge: %s exits 2 before any mint" % name):
                self.assertNoChild(self.run_tool("gh", "issue", "list"), says)
                self.assertEqual(self.server.calls, [])
        self.setUp()
        for name, repo, args, says in (
                ("user mode", self.new_repo("https://github.com/o/r.git", identity="user",
                                            forge="github", bot_login="roz-bot", bot_app_id="1"),
                 ("gh", "issue", "list"), "not `bot`"),
                ("no bot_app_id", self.new_repo("https://github.com/o/r.git", forge="github",
                                                bot_login="roz-bot"),
                 ("gh", "issue", "list"), "bot_app_id"),
                ("glab under forge: github", self.repo, ("glab", "issue", "list"), "forge: github"),
                ("a GitHub Enterprise origin", self.new_repo(
                    "https://ghe.corp.example/o/r.git", forge="github", bot_login="roz-bot",
                    bot_app_id="1"), ("gh", "issue", "list"), "not github.com"),
                ("an unreadable origin", self.new_repo("file:///tmp/x", forge="github",
                                                       bot_login="roz-bot", bot_app_id="1"),
                 ("gh", "issue", "list"), "origin"),
                ("no config block", Path(tempfile.mkdtemp(dir=str(self.tmp))),
                 ("gh", "issue", "list"), "config"),
        ):
            with self.subTest("roz-forge: %s exits 2, no child, no mint" % name):
                self.assertNoChild(self.run_tool(*args, cwd=repo), says)
                self.assertEqual(self.server.calls, [])
        with self.subTest("roz-forge: any word but gh / glab / git push is usage (64)"):
            for args in (("curl", "x"), ("git", "fetch"), ()):
                self.assertEqual(self.run_tool(*args).returncode, 64 if args else 64)
                self.assertEqual(self.children(), [])

    def test_glab_token_file_shape(self):
        repo = self.new_repo("https://gitlab.com/g/p.git", forge="gitlab", bot_login="pb")
        tok = self.home / ".config" / "roz-gate" / "pb.token"
        tok.write_text("two words\n")
        tok.chmod(0o600)
        with self.subTest("roz-forge glab: a token file holding more than one token is refused"):
            self.assertNoChild(self.run_tool("glab", "issue", "list", cwd=repo), "no single token")


class KeyPath(ForgeTest):
    def test_first_login_and_override(self):
        repo = self.new_repo("https://github.com/o/r.git", forge="github",
                             bot_login="roz-bot, other-bot", bot_app_id="123")
        with self.subTest("roz-forge: several bot_logins → the first names the key file"):
            self.assertEqual(self.run_tool("gh", "issue", "list", cwd=repo).returncode, 0)
        moved = self.tmp / "elsewhere.pem"
        self.key.rename(moved)
        local = repo / ".claude" / "roz-gate.local.json"
        local.parent.mkdir()
        local.write_text(json.dumps({"bot_key": str(moved)}))
        with self.subTest("roz-forge: `bot_key` in the local file overrides the default path"):
            self.assertEqual(self.run_tool("gh", "issue", "list", cwd=repo).returncode, 0)
        wt = self.tmp / "wt"
        subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "--allow-empty", "-m", "i"], check=True)
        subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", str(wt)], check=True,
                       capture_output=True)
        with self.subTest("roz-forge: a linked worktree finds `bot_key` in the main checkout"):
            p = self.run_tool("gh", "issue", "list", cwd=wt)
            self.assertEqual(p.returncode, 0, p.stderr)
        (repo / "keys").mkdir()
        moved.rename(repo / "keys" / "bot.pem")
        local.write_text(json.dumps({"bot_key": "keys/bot.pem"}))
        (repo / "sub").mkdir()
        for where, cwd in (("a subdirectory", repo / "sub"), ("a linked worktree", wt)):
            with self.subTest("roz-forge: a relative `bot_key` is the repository's, found from "
                              "%s (codex review, PR #424)" % where):
                p = self.run_tool("gh", "issue", "list", cwd=cwd)
                self.assertEqual(p.returncode, 0, p.stderr)


class Push(ForgeTest):
    def test_push(self):
        before = (self.repo / ".git" / "config").read_bytes()
        p = self.run_tool("git", "push", "-u", "origin", "feat/5")
        with self.subTest("roz-forge git push: keeps `-u origin <branch>`, the URL rides in "
                          "remote.origin.pushurl without a credential"):
            self.assertEqual(p.returncode, 0, p.stderr)
            (child,) = self.children()
            argv = child["argv"]
            self.assertEqual(argv[-4:], ["push", "-u", "origin", "feat/5"])
            self.assertIn("remote.origin.pushurl=https://github.com/o/r.git", argv)
            self.assertNotIn("@", " ".join(a for a in argv if "pushurl" in a))
        with self.subTest("roz-forge git push: stored helpers reset, then the one-shot helper"):
            cfg = [argv[i + 1] for i, a in enumerate(argv) if a == "-c"]
            self.assertIn("credential.helper=", cfg)
            self.assertLess(cfg.index("credential.helper="),
                            max(i for i, c in enumerate(cfg) if "ROZ_FORGE_TOKEN" in c))
        with self.subTest("roz-forge git push: the token only in git's env, ambient git auth gone"):
            env = child["env"]
            self.assertEqual(env["ROZ_FORGE_TOKEN"], TOKEN)
            self.assertEqual(env["GIT_TERMINAL_PROMPT"], "0")
            self.assertNotIn(HUMAN, json.dumps(env))
            for k in ("GIT_ASKPASS", "SSH_ASKPASS", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT",
                      "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0"):
                self.assertNotIn(k, env)
            self.assertNotIn(TOKEN, json.dumps(argv) + p.stdout + p.stderr)
            self.assertNotIn(TOKEN, json.dumps(p.after_env))
        with self.subTest("roz-forge git push: .git/config is byte-identical afterwards"):
            self.assertEqual((self.repo / ".git" / "config").read_bytes(), before)

    def test_ssh_origin(self):
        repo = self.new_repo("git@github.com:o/r.git", forge="github", bot_login="roz-bot",
                             bot_app_id="123")
        with self.subTest("roz-forge git push: an SSH origin pushes to its HTTPS twin"):
            p = self.run_tool("git", "push", "origin", "fix/9", cwd=repo)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("remote.origin.pushurl=https://github.com/o/r.git",
                          self.children()[0]["argv"])

    def test_https_port_kept(self):
        repo = self.new_repo("https://gitlab.example.com:8443/g/p.git", forge="gitlab",
                             bot_login="pb")
        tok = self.home / ".config" / "roz-gate" / "pb.token"
        tok.write_text("glpat-dummy\n")
        tok.chmod(0o600)
        with self.subTest("roz-forge git push: an HTTPS origin's explicit port is kept "
                          "(codex review, PR #424)"):
            p = self.run_tool("git", "push", "origin", "fix/9", cwd=repo)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("remote.origin.pushurl=https://gitlab.example.com:8443/g/p.git",
                          self.children()[0]["argv"])

    def test_refused_shapes(self):
        for args, says in ((("git", "push"), "usage"),
                           (("git", "push", "origin"), "usage"),
                           (("git", "push", "upstream", "feat/5"), "usage"),
                           (("git", "push", "origin", "a", "b"), "usage"),
                           (("git", "push", "--force", "origin", "feat/5"), "usage"),
                           (("git", "push", "--delete", "origin", "feat/5"), "usage"),
                           (("git", "push", "origin", "feat/5:main"), "plain branch"),
                           (("git", "push", "origin", "+feat/5"), "plain branch"),
                           (("git", "push", "origin", "--tags"), "plain branch")):
            with self.subTest("roz-forge git push: %s refused, no mint, no push"
                              % " ".join(args[1:])):
                self.assertNoChild(self.run_tool(*args), says)
                self.assertEqual(self.server.calls, [])

    def test_refused_destinations(self):
        subprocess.run(["git", "-C", str(self.repo), "config", "remote.origin.pushurl",
                        "https://github.com/o/mirror.git"], check=True)
        with self.subTest("roz-forge git push: an existing pushurl is refused "
                          "(a second destination)"):
            self.assertNoChild(self.run_tool("git", "push", "origin", "feat/5"), "pushurl")
        repo = self.new_repo("https://github.com/o/r.git", forge="github", bot_login="roz-bot",
                             bot_app_id="123")
        subprocess.run(["git", "-C", str(repo), "config", "url.https://evil.example/.insteadOf",
                        "https://github.com/"], check=True)
        with self.subTest("roz-forge git push: an insteadOf rewrite of the URL is refused"):
            self.assertNoChild(self.run_tool("git", "push", "origin", "feat/5", cwd=repo),
                               "insteadOf")
        self.assertEqual(self.server.calls, [])


class CredentialFill(ForgeTest):
    """The real git resolves the one-shot helper over every stored one."""

    def test_fill_and_approve(self):
        import importlib.machinery
        import importlib.util
        loader = importlib.machinery.SourceFileLoader("roz_forge", str(TOOL))
        spec = importlib.util.spec_from_loader("roz_forge", loader)
        mod = importlib.util.module_from_spec(spec)
        loader.exec_module(mod)
        store = self.tmp / "human-store"
        store.write_text("https://human:storedpw@github.com\n")
        glob = self.tmp / "global.gitconfig"
        glob.write_text('[credential]\n'
                        '\thelper = "!f() { echo username=human; echo password=humanpw; }; f"\n'
                        '[credential "https://github.com"]\n\thelper = store --file=%s\n' % store)
        env = dict(os.environ, HOME=str(self.home), GIT_CONFIG_GLOBAL=str(glob),
                   GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0", ROZ_FORGE_TOKEN=TOKEN)
        cwd = os.getcwd()
        os.chdir(str(self.repo))
        try:
            old = os.environ.get("GIT_CONFIG_GLOBAL")
            os.environ["GIT_CONFIG_GLOBAL"] = str(glob)
            args = mod.helper_config("x-access-token")
        finally:
            os.chdir(cwd)
            os.environ.pop("GIT_CONFIG_GLOBAL") if old is None else os.environ.update(
                GIT_CONFIG_GLOBAL=old)
        with self.subTest("roz-forge: URL-scoped stored helpers are found and reset"):
            self.assertIn("credential.https://github.com.helper=", args)
        fill = subprocess.run(["git", *args, "credential", "fill"], cwd=str(self.repo), env=env,
                              input="protocol=https\nhost=github.com\n\n", capture_output=True,
                              text=True)
        with self.subTest("roz-forge: real `git credential fill` answers with the bot, not a "
                          "stored human helper"):
            self.assertEqual(fill.returncode, 0, fill.stderr)
            self.assertIn("username=x-access-token\n", fill.stdout)
            self.assertIn("password=%s\n" % TOKEN, fill.stdout)
            self.assertNotIn("human", fill.stdout)
        approve = subprocess.run(["git", *args, "credential", "approve"], cwd=str(self.repo),
                                 env=env, input=fill.stdout + "\n", capture_output=True, text=True)
        with self.subTest("roz-forge: `credential approve` stores nothing anywhere"):
            self.assertEqual(approve.returncode, 0, approve.stderr)
            self.assertEqual(store.read_text(), "https://human:storedpw@github.com\n")
            self.assertEqual(sorted(p.name for p in (self.home / ".config" / "roz-gate").iterdir()),
                             ["roz-bot.pem"])


class GitAuth(BaseHTTPRequestHandler):
    """A git smart-HTTP endpoint that wants Basic auth: 401 until it gets one."""

    def log_message(self, *a):
        pass

    def do_GET(self):
        auth = self.headers.get("Authorization", "")
        self.server.seen.append(auth)
        if not auth.startswith("Basic "):
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="x"')
            self.end_headers()
            return
        self.send_response(404)
        self.end_headers()


class StoredHeaders(ForgeTest):
    """Real git against a local HTTP server: a stored `Authorization` extra
    header (generic or URL-scoped) never rides along, nor a `~/.netrc` entry
    for the host; the bot's Basic auth does (codex review, PR #424)."""

    def test_extra_headers_reset(self):
        import base64
        import importlib.machinery
        import importlib.util
        srv = HTTPServer(("127.0.0.1", 0), GitAuth)
        srv.seen = []
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        url = "http://127.0.0.1:%d/o/r.git" % srv.server_port
        glob = self.tmp / "global.gitconfig"
        glob.write_text('[http]\n\textraHeader = "Authorization: Bearer human-generic"\n'
                        '[http "http://127.0.0.1:%d/"]\n'
                        '\textraHeader = "Authorization: Bearer human-scoped"\n'
                        % srv.server_port)
        loader = importlib.machinery.SourceFileLoader("roz_forge", str(TOOL))
        spec = importlib.util.spec_from_loader("roz_forge", loader)
        mod = importlib.util.module_from_spec(spec)
        loader.exec_module(mod)
        netrc = self.home / ".netrc"
        netrc.write_text("machine 127.0.0.1 login human password humanpw\n")
        netrc.chmod(0o600)
        empty = Path(tempfile.mkdtemp(dir=str(self.tmp)))
        cwd = os.getcwd()
        saved = {k: os.environ.get(k) for k in ("GIT_CONFIG_GLOBAL", "HOME")}
        os.chdir(str(self.repo))
        os.environ.update(GIT_CONFIG_GLOBAL=str(glob), HOME=str(self.home))
        try:
            args = mod.helper_config("x-access-token")
            env = mod.push_env(TOKEN, str(empty))
        finally:
            os.chdir(cwd)
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        env["GIT_CONFIG_NOSYSTEM"] = "1"
        with self.subTest("roz-forge: the push child's HOME is empty; the global config stays"):
            self.assertEqual(env["HOME"], str(empty))
            self.assertEqual(env["GIT_CONFIG_GLOBAL"], str(glob))
        subprocess.run(["git", *args, "ls-remote", url], cwd=str(self.repo), env=env,
                       capture_output=True, text=True, timeout=30)
        want = "Basic " + base64.b64encode(("x-access-token:%s" % TOKEN).encode()).decode()
        sent = [base64.b64decode(a[6:]).decode() if a.startswith("Basic ") else a
                for a in srv.seen]
        with self.subTest("roz-forge: no stored Authorization header and no netrc entry "
                          "reaches the server"):
            self.assertTrue(srv.seen, "git made no request")
            self.assertFalse([a for a in sent if "human" in a], sent)
        with self.subTest("roz-forge: the server got the bot's Basic auth from the one-shot "
                          "helper"):
            self.assertIn(want, srv.seen)


class PushGlobalConfig(ForgeTest):
    def test_both_global_files_survive_the_empty_home(self):
        import importlib.machinery
        import importlib.util
        loader = importlib.machinery.SourceFileLoader("roz_forge", str(TOOL))
        spec = importlib.util.spec_from_loader("roz_forge", loader)
        mod = importlib.util.module_from_spec(spec)
        loader.exec_module(mod)
        (self.home / ".gitconfig").write_text("[http]\n\tsslCAInfo = /corp/ca.pem\n")
        (self.home / ".config" / "git").mkdir(parents=True)
        (self.home / ".config" / "git" / "config").write_text(
            "[http]\n\tproxy = http://proxy:3128\n")
        empty = Path(tempfile.mkdtemp(dir=str(self.tmp)))
        saved = {k: os.environ.get(k) for k in ("HOME", "GIT_CONFIG_GLOBAL", "XDG_CONFIG_HOME")}
        os.environ["HOME"] = str(self.home)
        os.environ.pop("GIT_CONFIG_GLOBAL", None)
        os.environ.pop("XDG_CONFIG_HOME", None)
        try:
            env = mod.push_env(TOKEN, str(empty))
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        env["GIT_CONFIG_NOSYSTEM"] = "1"

        def get(key):
            return subprocess.run(["git", "config", "--get", key], cwd=str(self.repo), env=env,
                                  capture_output=True, text=True).stdout.strip()
        with self.subTest("roz-forge: the push child still reads ~/.gitconfig and the XDG "
                          "config (codex review, PR #424)"):
            self.assertEqual(get("http.sslCAInfo"), "/corp/ca.pem")
            self.assertEqual(get("http.proxy"), "http://proxy:3128")
        with self.subTest("roz-forge: the push child's HOME holds no .netrc"):
            self.assertEqual(sorted(p.name for p in empty.iterdir()), [".gitconfig"])


class NoCache(ForgeTest):
    def test_nothing_written(self):
        def tree():
            return sorted(str(p.relative_to(self.home)) for p in self.home.rglob("*"))
        before = tree()
        self.run_tool("gh", "issue", "list")
        self.run_tool("gh", "issue", "list")
        with self.subTest("roz-forge: two calls mint twice and write nothing under HOME"):
            self.assertEqual(tree(), before)
            self.assertEqual(sum(1 for m, _, _ in self.server.calls if m == "POST"), 2)


if __name__ == "__main__":
    unittest.main()
