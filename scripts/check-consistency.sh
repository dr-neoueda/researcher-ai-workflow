#!/usr/bin/env bash
# check-consistency.sh — release-hygiene guard for the raw distribution.
#
# Catches the recurring manual-mirroring mistakes:
#   1. plugin version vs marketplace version drift
#   2. plugin <-> codex-plugin shared-asset drift (references/ + templates/ must
#      stay byte-identical; SKILL.md legitimately differs per CLI so is excluded)
#   3. personalization leaks in the distributed tree (author / lab / compounds)
#
# Usage:  bash scripts/check-consistency.sh
# Exit:   0 = all good, non-zero = at least one problem (CI-friendly).

set -u
cd "$(dirname "$0")/.." || exit 2
fail=0
red=$'\033[0;31m'; grn=$'\033[0;32m'; dim=$'\033[2m'; off=$'\033[0m'
ok()   { printf '%s OK %s %s\n' "$grn" "$off" "$*"; }
bad()  { printf '%s BAD%s %s\n' "$red" "$off" "$*"; fail=1; }

json_version() { # $1 = file
  grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "$1" | head -1 | sed 's/.*"\([^"]*\)"$/\1/'
}

# --- 1. plugin vs marketplace version ---
pv=$(json_version plugin/.claude-plugin/plugin.json)
mv=$(json_version .claude-plugin/marketplace.json)
cv=$(json_version codex-plugin/.codex-plugin/plugin.json)
cpv=$(json_version copilot-plugin/plugin.json)
gv=$(json_version gemini-plugin/gemini-extension.json)
if [ -n "$pv" ] && [ "$pv" = "$mv" ]; then
  ok "plugin version == marketplace version ($pv)"
else
  bad "plugin ($pv) != marketplace ($mv) — bump both together"
fi
printf '%s    codex-plugin version: %s%s\n' "$dim" "${cv:-?}" "$off"
printf '%s    copilot-plugin version: %s (enterprise track)%s\n' "$dim" "${cpv:-?}" "$off"

# Copilot ships from its own marketplace manifest (.github/plugin/marketplace.json).
# It drifted silently from 1.17.0 while the plugin reached 1.44.0 because nothing compared them.
cpmv=$(json_version .github/plugin/marketplace.json)
if [ -n "$cpv" ] && [ "$cpv" = "$cpmv" ]; then
  ok "copilot-plugin version == copilot marketplace version ($cpv)"
else
  bad "copilot-plugin ($cpv) != .github/plugin/marketplace.json ($cpmv) — bump both together"
fi

# gemini-plugin is FROZEN (see gemini-plugin/FROZEN.md). Do not follow plugin changes
# or bump its version. Report how far behind it has drifted so the gap stays visible.
frozen_file="gemini-plugin/FROZEN.md"
if [ -f "$frozen_file" ]; then
  fdate=$(sed -n 's/^frozen_date:[[:space:]]*//p' "$frozen_file" | head -1)
  fplug=$(sed -n 's/^frozen_at_plugin_version:[[:space:]]*//p' "$frozen_file" | head -1)
  # minor-version gap between the plugin version at freeze time and the current one
  f_minor=$(printf '%s' "$fplug" | cut -d. -f2)
  p_minor=$(printf '%s' "$pv"    | cut -d. -f2)
  f_major=$(printf '%s' "$fplug" | cut -d. -f1)
  p_major=$(printf '%s' "$pv"    | cut -d. -f1)
  if [ "$f_major" = "$p_major" ] && [ -n "$f_minor" ] && [ -n "$p_minor" ]; then
    gap=$((p_minor - f_minor))
  else
    gap="?"
  fi
  printf '%s    gemini-plugin version: %s (FROZEN %s at plugin %s; plugin now %s, %s minor behind)%s\n' \
    "$dim" "${gv:-?}" "${fdate:-?}" "${fplug:-?}" "${pv:-?}" "$gap" "$off"
  if [ "$gap" != "?" ] && [ "$gap" -ge 20 ] 2>/dev/null; then
    printf '%s    NOTE: gemini-plugin is %s minor versions behind — revisit gemini-plugin/FROZEN.md%s\n' \
      "$dim" "$gap" "$off"
  fi
else
  printf '%s    gemini-plugin version: %s (extension)%s\n' "$dim" "${gv:-?}" "$off"
fi

# --- 2. plugin <-> codex mirror (byte-identical shared assets only) ---
mirror_dirs=(
  "skills/raw-slides/references"
  "skills/raw-slides/scripts"
  "skills/raw-slides/vendor"
  "skills/raw-analyze/references"
  "skills/raw-write/scripts"
  "skills/raw-write/tests"
)
for d in "${mirror_dirs[@]}"; do
  p="plugin/$d"; c="codex-plugin/$d"
  if [ ! -d "$p" ] || [ ! -d "$c" ]; then
    printf '%s    skip mirror %s (missing)%s\n' "$dim" "$d" "$off"; continue
  fi
  # Exclude build/run artifacts (all gitignored): bytecode + smoke-test output.
  dx=(-x '__pycache__' -x '*.pyc' -x 'presentations')
  if diff -r -q "${dx[@]}" "$p" "$c" >/dev/null 2>&1; then
    ok "mirror identical: $d"
  else
    bad "mirror DRIFT: $d (plugin vs codex-plugin differ)"
    diff -r -q "${dx[@]}" "$p" "$c" 2>&1 | sed 's/^/      /'
  fi
done

# --- 2a. plugin <-> codex single shared files (byte-identical) ---
# HTML design contract: all HTML-producing skills follow it, so plugin and codex
# must carry the exact same file (Gemini inlines it in GEMINI.md separately).
for f in skills/raw/references/html-style.md skills/raw/references/playbook-web-seeding.md skills/raw/references/field-rules.md skills/raw/scripts/scaffold.py; do
  pf="plugin/$f"; cf="codex-plugin/$f"
  if [ ! -f "$pf" ] || [ ! -f "$cf" ]; then
    printf '%s    skip mirror %s (missing)%s\n' "$dim" "$f" "$off"; continue
  fi
  if diff -q "$pf" "$cf" >/dev/null 2>&1; then
    ok "mirror identical: $f"
  else
    bad "mirror DRIFT: $f (plugin vs codex-plugin differ)"
  fi
done

# copilot-plugin is PAUSED (see copilot-plugin/PAUSED.md): development continues on
# Claude Code + Codex only, so the codex <-> copilot mirror checks (2b, 2c) are
# skipped until the pause is lifted. Report the gap so it stays visible.
paused_file="copilot-plugin/PAUSED.md"
if [ -f "$paused_file" ]; then
  pplug=$(sed -n 's/^paused_at_plugin_version:[[:space:]]*//p' "$paused_file" | head -1)
  printf '%s    copilot mirror checks skipped (PAUSED at plugin %s; plugin now %s — see %s)%s\n' \
    "$dim" "${pplug:-?}" "${pv:-?}" "$paused_file" "$off"
else

# --- 2b. codex <-> copilot shared reference files ---
# copilot-plugin reuses codex's CLI-agnostic templates verbatim.
# (mcp-setup-templates.md intentionally differs per CLI and is NOT enforced here.)
for f in skills/raw/references/agents-md-template.md skills/raw/references/playbook-starters.md skills/raw/references/job-hunting-departments.md skills/raw/references/engine-validation-map.md skills/raw/references/playbook-web-seeding.md skills/raw/references/html-style.md skills/raw/references/research-departments.md skills/raw/references/field-rules.md skills/raw/scripts/scaffold.py; do
  cf="codex-plugin/$f"; pf="copilot-plugin/$f"
  if [ ! -f "$cf" ] || [ ! -f "$pf" ]; then
    printf '%s    skip copilot mirror %s (missing)%s\n' "$dim" "$f" "$off"; continue
  fi
  if diff -q "$cf" "$pf" >/dev/null 2>&1; then
    ok "copilot mirror identical: $f"
  else
    bad "copilot mirror DRIFT: $f (codex vs copilot differ)"
  fi
done

# --- 2c. codex <-> copilot skill directories (byte-identical) ---
# The 2026-08-21 full port copied these 13 skills verbatim from codex-plugin.
# raw/ and raw-setup/ are deliberately excluded: they carry Copilot-specific
# CLI names (copilot vs codex/claude) and must be maintained per variant.
for s in raw-research raw-register raw-write raw-input raw-playbook raw-analyze \
         raw-slides raw-doctor raw-intake raw-report raw-es raw-interview raw-events; do
  cd_="codex-plugin/skills/$s"; pd_="copilot-plugin/skills/$s"
  if [ ! -d "$cd_" ] || [ ! -d "$pd_" ]; then
    printf '%s    skip copilot skill mirror %s (missing)%s\n' "$dim" "$s" "$off"; continue
  fi
  if diff -r -q "$cd_" "$pd_" >/dev/null 2>&1; then
    ok "copilot skill mirror identical: $s"
  else
    bad "copilot skill mirror DRIFT: $s (codex vs copilot differ)"
  fi
done

fi  # copilot PAUSED

# --- 3. personalization leak scan (distributed tree only) ---
# Specific proper nouns only — generic field terms (MLIP/CP2K/DFT) are allowed.
# The author credit in the manifests is intentional and is the only allowed use of the name.
leak_re='aaBrAdox|SPReAD|Bis\(BrPhCH2O\)|NU-[0-9]|PILATUS|n267302|neoueda@|/Users/neoueda|上田|Ueda|9-CNAD|平野研'
hits=$(grep -RInE "$leak_re" plugin codex-plugin copilot-plugin gemini-plugin .github/plugin 2>/dev/null \
        | grep -v 'Binary file' | grep -v 'Shinno Ueda (UEC SPRING)' || true)
if [ -z "$hits" ]; then
  ok "no personalization leaks in plugin/, codex-plugin/, copilot-plugin/, gemini-plugin/, .github/plugin/"
else
  bad "personalization leak(s) found:"
  printf '%s\n' "$hits" | sed 's/^/      /'
fi

# --- 4. ABSOLUTE: no Finder/Explorer-invisible (dot-prefixed) ops folder ---
# raw must scaffold only VISIBLE folders in the user's project (ops dir = 'office/').
# Guard against regressing to the old hidden '.company/' name.
hidden=$(grep -RIn --exclude-dir=dist --exclude-dir=node_modules '\.company' plugin codex-plugin copilot-plugin gemini-plugin web docs README.md RESUME.md 2>/dev/null || true)
if [ -z "$hidden" ]; then
  ok "no hidden '.company' ops-folder references (visible 'office/' is used)"
else
  bad "hidden '.company' folder reference found — raw must scaffold the visible 'office/' dir:"
  printf '%s\n' "$hidden" | sed 's/^/      /'
fi

echo
if [ "$fail" -eq 0 ]; then printf '%sAll consistency checks passed.%s\n' "$grn" "$off"
else printf '%sConsistency checks FAILED — fix the BAD items above.%s\n' "$red" "$off"; fi
exit "$fail"
