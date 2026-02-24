# Mersea

Bridge between local `.mmd` files and [mermaid.ai](https://mermaid.ai/play) visual editor. Open a file, edit the diagram visually in the browser, Ctrl+S saves back to disk.

No dependencies beyond Python 3.11+ and Chromium.

## Quickstart

```bash
git clone https://github.com/ftelnov/mersea.git
cd mersea
pip install .
mersea /path/to/diagram.mmd
```

Or with pipx:

```bash
pipx install git+https://github.com/ftelnov/mersea.git
mersea /path/to/diagram.mmd
```

Browser opens fullscreen with your diagram loaded in mermaid.ai/play. Edit visually, then:

- **Ctrl+S** or click **Save** — saves to disk
- **Save & Close** — saves and exits
- Close the browser tab — mersea exits automatically

Requires Chromium (or Google Chrome) on PATH.

## Nix

```bash
nix run github:ftelnov/mersea -- /path/to/diagram.mmd
```

Use as a flake input:

```nix
inputs.mersea.url = "github:ftelnov/mersea";
inputs.mersea.inputs.nixpkgs.follows = "nixpkgs";

# Then use:
inputs.mersea.packages.${pkgs.system}.default
```

## How it works

1. Reads `.mmd` file and encodes it into a pako URL (same format mermaid.live uses)
2. Starts a local HTTP server for save callbacks
3. Generates a temporary Chrome extension with save UI (Ctrl+S, save button, toast notifications)
4. Launches Chromium with `--load-extension` pointing to the temp extension
5. On save: extension POSTs URL hash to localhost, Python decodes pako and writes to file
6. When the browser closes, mersea cleans up and exits
