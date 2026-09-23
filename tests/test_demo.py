from pathlib import Path

from PIL import Image

from telecom_twin.demo import export_demo_gif


def test_demo_gif_uses_multiple_replay_frames(tmp_path: Path) -> None:
    path = export_demo_gif(tmp_path / "demo.gif")
    assert path.exists() and path.stat().st_size > 0
    with Image.open(path) as image:
        assert image.n_frames >= 20
        assert image.size[0] >= 800
