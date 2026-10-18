# GOKPOP public site watchdog

Checks only the public GOKPOP page. It never changes scores, application data,
Git history or Streamlit deployment settings and needs no application secrets.

## Run manually

```bash
python -m pip install -r ops/streamlit_watchdog/requirements.txt
python -m playwright install --with-deps chromium
python -m unittest discover -s ops/streamlit_watchdog -p 'test_*.py' -v
python ops/streamlit_watchdog/check_site.py --output-dir /tmp/gokpop-check-unique-run
```

Use a **new** output directory each time. On Windows, use an appropriate new
local path and `python -m playwright install chromium`.

The browser must see GOKPOP 2.0, 69.44/100 and all three menu controls in the same
app frame. App exceptions take priority over a matching score. A sleep message
and the exact visible `Yes, get this app back up!` button are both required for
one click. Clicking alone is not success: the app must then load normally.

Initial UI wait: 90 seconds. Post-click wait: 240 seconds. DOM poll: 5 seconds
without refreshing. Navigation timeout: 45 seconds, one transport retry after
15 seconds. HTTP errors are not retried. YouTube/media are blocked in this
health check to reduce unnecessary requests; this does not test video playback.

`result.json`, `events.json`, visible public text and screenshot(s) are stored.
No cookies, storage, response bodies, API keys or HAR/trace are collected.
Exit 0 means healthy; exit 1 means failure. Actual Cloud waking and localhost
fixture results must always be reported separately.

## GitHub activation (requires user approval before publishing)

1. Put the workflow and this directory on the repository's actual default branch
   (`master` was verified on 2026-10-18).
2. Keep repository variable `GOKPOP_WATCHDOG_ENABLED` unset or `false`.
3. Actions → GOKPOP Streamlit watchdog → Run workflow → default branch.
4. Check a successful **real GitHub runner** result and diagnostics artifact.
5. Enable Email/Web Actions notifications and failures-only notifications in
   GitHub account settings. Confirm delivery on a real failed run; a failed
   localhost fixture is not proof that email delivery works.
6. After approval and successful manual run, set the repository Actions variable
   `GOKPOP_WATCHDOG_ENABLED=true` to allow scheduled browser jobs.

Cron: `17 */6 * * *`, UTC. Four opportunities per day, KST 03:17, 09:17,
15:17, 21:17. The scheduled job is gated off until the variable is enabled.
GitHub may delay or drop scheduled runs and can disable schedules after 60 days
without repository activity. Do not create artificial commits to avoid this.

To disable: Actions → workflow → `…` → Disable workflow. Alternatively set the
variable to `false` to skip scheduled browser jobs while preserving manual runs.
No checkout credentials are persisted, only `contents: read` is granted, and
there is no push/PR/deploy step. Diagnostics artifacts expire after 7 days.

## Policy and operating limits

- [Streamlit app hibernation](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app#app-hibernation)
  documents inactivity sleep, browser visits and the public wake button.
- [Streamlit terms](https://streamlit.io/terms-of-use) prohibit interference,
  security bypass and unauthorized access. This is a low-frequency normal
  Chromium visit, not a private wake endpoint or an anti-bot bypass.
- These documents do not provide a specific approval or availability guarantee
  for this six-hour automated monitor. Stop if platform policy or restrictions
  change. Never bypass authentication, CAPTCHA, rate limiting or errors.
- [GitHub schedule limits](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [GitHub workflow notifications](https://docs.github.com/en/actions/concepts/workflows-and-actions/notifications-for-workflow-runs)
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)

Four checks/day is 120 runs per 30-day month, plus manual runs. Standard Linux
runners on public repositories have free execution minutes; artifact storage
limits still apply. Actual runner minutes and email delivery are unverified
until this workflow is published and manually run. A 15-minute job limit bounds
each run; normal execution should be shorter and must be measured after launch.
