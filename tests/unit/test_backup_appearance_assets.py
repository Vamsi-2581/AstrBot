from pathlib import Path

from astrbot.core.backup.constants import get_backup_directories


def test_backup_directories_include_dashboard_appearance_assets():
    directories = get_backup_directories()
    assert "dashboard" in directories
    assert Path(directories["dashboard"]).parts[-2:] == ("data", "dashboard")
