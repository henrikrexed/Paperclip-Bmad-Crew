# BMAD custom overrides

Place team-level skill overrides here as `<skill-name>.toml`.
Place personal overrides here as `<skill-name>.user.toml`.

Installed BMAD skills read these files through `_bmad/scripts/resolve_customization.py` using this merge order:

1. Skill defaults: `<skill-root>/customize.toml`
2. Team override: `_bmad/custom/<skill-name>.toml`
3. Personal override: `_bmad/custom/<skill-name>.user.toml`

Merge rules: scalars override, objects merge recursively, arrays append.

Do not commit secrets. Use Paperclip secrets or environment variables for tokens and API keys.
