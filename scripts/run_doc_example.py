import sys
from pathlib import Path

from idom.widgets.utils import hotswap
from idom.server.sanic import PerClientStateServer

here = Path(__file__).parent
examples_dir = here.parent / "docs" / "source" / "examples"
sys.path.insert(0, str(examples_dir))

for file in examples_dir.iterdir():
    if not file.is_file() or not file.suffix == ".py" or file.stem.startswith("_"):
        continue


def main():
    ex_name = sys.argv[1]
    example_file = examples_dir / (ex_name + ".py")

    if not example_file.exists():
        print(f"No example {ex_name!r} exists. Choose from:")
        for found_example_file in examples_dir.glob("*.py"):
            print("-", found_example_file.stem)
        return

    mount, element = hotswap()
    server = PerClientStateServer(element)

    with example_file.open() as f:
        exec(
            f.read(),
            {
                "display": mount,
                "__file__": str(file),
                "__name__": f"widgets.{file.stem}",
            },
        )

    server.run("127.0.0.1", 5000)


if __name__ == "__main__":
    main()
