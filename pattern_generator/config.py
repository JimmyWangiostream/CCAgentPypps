from pathlib import Path
from dataclasses import dataclass, field

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class PGConfig:
    repo_root: Path = field(default_factory=lambda: REPO_ROOT)
    wiki_path: Path = field(default_factory=lambda: REPO_ROOT / "wiki")
    # Generated artifacts live inside the Script/ tree so the final pattern .py
    # can be type-checked (mypy) and indexed alongside real patterns. The final
    # .py lands directly in generated/; each run's by-products go in a per-pattern
    # subfolder (generated/<pattern_id>/).
    generated_dir: Path = field(
        default_factory=lambda: REPO_ROOT / "GitNexusMCP" / "Script" / "pattern" / "generated")
    # Root of the grounded Script/ library (gitnexus-indexed), used by the
    # api-grounding reality check in the validator.
    script_root: Path = field(default_factory=lambda: REPO_ROOT / "GitNexusMCP" / "Script")
    # Code-grounding source for unit prompts:
    #   "gitnexus" (default) — prompt tells the model to call the gitnexus MCP tools
    #   "direct"             — inject top-N candidate symbols retrieved straight from
    #                          script_root (code_retrieval); no MCP server involved.
    grounding_mode: str = "gitnexus"

    def __post_init__(self):
        self.repo_root = Path(self.repo_root)
        self.wiki_path = Path(self.wiki_path)
        self.generated_dir = Path(self.generated_dir)
        self.script_root = Path(self.script_root)
        self.generated_dir.mkdir(parents=True, exist_ok=True)
