# Mersea

Bridge between local `.mmd` files and [mermaid.ai](https://mermaid.ai/play) visual editor. Open a file, edit the diagram visually in the browser, Ctrl+S saves back to disk.

## Quickstart

```bash
# Install dependencies
cd ~/Projects/mersea && poetry install

# Install Playwright browser (first time only)
poetry run playwright install chromium

# Open a diagram
echo -e "graph TD\n    A-->B" > /tmp/test.mmd
poetry run mersea /tmp/test.mmd
```

Browser opens fullscreen with your diagram loaded in mermaid.ai/play. Edit visually, then:

- **Ctrl+S** or click **Save** — saves to disk
- **Save & Close** — saves and exits
- Close the browser tab — mersea exits automatically

## Nix

```bash
# Build
nix build

# Run directly
nix run . -- /tmp/test.mmd
```

Use as a flake input:

```nix
# flake.nix
inputs.mersea.url = "path:/home/fedor/Projects/mersea";

# home.nix or wherever
inputs.mersea.packages.${pkgs.system}.default
```

## How it works

1. Reads `.mmd` file and encodes it into a pako URL (same format mermaid.live uses)
2. Launches Chromium via Playwright with a persistent profile (login cookies survive between sessions)
3. Navigates to `mermaid.ai/play#pako:...`
4. Injects save handler via CDP (bypasses CSP)
5. On save: reads URL hash (updated in real-time by the editor), decodes pako, writes to file
