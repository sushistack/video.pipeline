import pytest
from unittest.mock import MagicMock, patch, ANY, call
from pathlib import Path
import json

from core.gen_capcut import CapCutGenerator
import pycapcut as cc

@pytest.fixture
def mock_pycapcut():
    with patch('core.gen_capcut.cc') as mock_cc:
        # Mock Enums
        mock_cc.TrackType.video = "video"
        mock_cc.TrackType.audio = "audio"
        mock_cc.TrackType.text = "text"
        
        # Mock Timerange
        mock_cc.Timerange.return_value = MagicMock()
        
        yield mock_cc

@pytest.fixture
def mock_root(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    return root

@pytest.fixture
def generator(mock_root, mock_pycapcut):
    # Mock environment resolution
    with patch('core.gen_capcut.CapCutGenerator._resolve_drafts_root') as mock_resolve:
        mock_resolve.return_value = Path("/mock/capcut/drafts")
        
        # Configure DraftFolder on the mock_cc object
        mock_folder = MagicMock()
        mock_folder.folder_path = "/mock/capcut/drafts"
        mock_pycapcut.DraftFolder.return_value = mock_folder
        
        gen = CapCutGenerator(mock_root)
        return gen

def test_initialization(generator):
    """Test that generator initializes with correct output root and draft folder."""
    assert generator.output_root.name == "workspace"
    assert generator.folder is not None
    assert generator.folder.folder_path == "/mock/capcut/drafts"

def test_resolve_drafts_root_success(mock_pycapcut):
    """Test finding a valid draft root."""
    # Since we mock 'cc', the internal check in __init__ uses mock_cc.DraftFolder
    # But we need to verify finding REAL paths?
    # No, the method _resolve_drafts_root uses os.environ/Path.home etc.
    # The __init__ CALLS DraftFolder.
    
    # We want to test logic inside _resolve_drafts_root mostly?
    # But this test calls __init__ which calls DraftFolder.
    # mock_pycapcut handles the DraftFolder call.
    
    with patch('pathlib.Path.exists', return_value=True):
         with patch('pathlib.Path.home', return_value=Path("/Users/test")):
             # We need to un-mock _resolve_drafts_root for this test instance?
             # generator fixture mocks it. But here we manually instantiate.
             gen = CapCutGenerator(Path("/tmp"))
             assert gen.drafts_root is not None

def test_initialize_script(generator):
    """Test script creation."""
    generator.folder.create_draft.return_value = MagicMock()
    
    generator._initialize_script("TestProject")
    
    generator.folder.create_draft.assert_called_once_with(
        "TestProject", width=1920, height=1080, fps=30, allow_replace=True
    )
    assert generator.script is not None
    assert generator.draft_name == "TestProject"

def test_add_media_tracks(generator, mock_pycapcut):
    """Test adding audio and video tracks."""
    project_name = "TestProject"
    
    # Mock Files
    project_dir = generator.output_root / project_name
    (project_dir / "simulated").mkdir(parents=True)
    (project_dir / "audios" / "ja").mkdir(parents=True)
    
    # Create dummy files
    (project_dir / "simulated" / "video.mp4").touch()
    (project_dir / "audios" / "ja" / "audio.mp3").touch()
    
    # Mock Script and Tracks
    mock_script = MagicMock()
    # Ensure content dict exists for version sync
    mock_script.content = {} 
    
    # Mock template file read
    mock_template_content = json.dumps({
        "new_version": "99.9.9",
        "version": 12345,
        "platform": {"app_version": "8.8.8"},
        "last_modified_platform": {"app_version": "8.8.8"}
    })
    
    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = mock_template_content
        mock_file.__enter__.return_value = mock_file
        # complex mock to handle json.load reading from file object
        # simpler: patch json.load?
        pass # moving to separate test or wrapping call
    
    generator.script = mock_script
    
    track_video = MagicMock()
    track_audio = MagicMock()
    mock_script.add_track.side_effect = [track_video, track_audio]
    
    # Mock Segments
    mock_audio_seg = MagicMock()
    mock_audio_seg.material.duration = 5000000 # 5s
    mock_pycapcut.AudioSegment.return_value = mock_audio_seg
    
    mock_video_seg = MagicMock()
    mock_video_seg.material.duration = 10000000 # 10s
    mock_pycapcut.VideoSegment.return_value = mock_video_seg
    
    # Execute
    generator.add_media_tracks(project_name)
    
    # Assertions
    assert mock_script.add_track.call_count == 2
    mock_pycapcut.AudioSegment.assert_called()
    mock_pycapcut.VideoSegment.assert_called()
    
    # Check segment addition
    track_audio.add_segment.assert_called_once()
    track_video.add_segment.assert_called_once()
    
    # Check save
    mock_script.save.assert_called_once()

def test_process_subtitles_yomigana(generator, mock_pycapcut):
    """Test subtitle processing with Yomigana mapping."""
    project_name = "TestProject"
    
    # Mock Subtitle File
    sub_dir = generator.output_root / project_name / "subtitles" / "synced"
    sub_dir.mkdir(parents=True)
    
    sub_data = [
        {
            "text": "漢字テスト",
            "kanjis": [
                {"kanji": "漢字", "yomigana": "かんじ"}
            ]
        }
    ]
    with open(sub_dir / "ja.json", "w", encoding="utf-8") as f:
        json.dump(sub_data, f)
        
    # Mock Script and Tracks
    mock_script = MagicMock()
    generator.script = mock_script
    
    # Mock Audio Track existing in script to provide timing
    mock_audio_track = MagicMock()
    mock_audio_track.type = "audio"
    mock_audio_seg = MagicMock()
    mock_audio_seg.target_timerange.start = 0
    mock_audio_seg.target_timerange.duration = 5000000
    mock_audio_track.segments = [mock_audio_seg]
    
    mock_script.tracks = [mock_audio_track]
    
    # Text input mock
    mock_main_track = MagicMock()
    mock_ruby_track = MagicMock()
    mock_script.add_track.side_effect = [mock_main_track, mock_ruby_track] # Main, then Ruby
    
    # Execute
    generator.process_subtitles(project_name)
    
    # Verify Main Text
    mock_pycapcut.TextSegment.assert_any_call(
        "漢字テスト", ANY, style=ANY
    )
    mock_main_track.add_segment.assert_called()
    
    # Verify Ruby (Yomigana)
    # "漢字" should trigger a ruby segment "かんじ"
    found_ruby = False
    for call_args in mock_pycapcut.TextSegment.call_args_list:
        if call_args[0][0] == "かんじ":
            found_ruby = True
            break
    assert found_ruby, "Yomigana segment not created"

def test_map_yomigana_logic(generator):
    """Unit test for _map_yomigana helper."""
    text = "今日は良い天気です"
    kanjis = [
        {"kanji": "今日", "yomigana": "きょう"},
        {"kanji": "天気", "yomigana": "てんき"}
    ]
    
    mapping = generator._map_yomigana(text, kanjis)
    
    # "今日" starts at 0, len 2
    assert 0 in mapping
    assert mapping[0] == ("きょう", 2, 0)
    
    # "天気" starts at 5 (今1,日1,は1,良1,い1) -> 5
    assert 5 in mapping
    assert mapping[5] == ("てんき", 2, 1)

def test_save_project(generator):
    """Test saving/exporting project backup."""
    project_name = "TestProject"
    
    # Ensure folder path is string
    generator.folder.folder_path = "/mock/capcut/drafts" 
    generator.draft_name = project_name
    
    mock_src = Path("/mock/capcut/drafts") / project_name
    
    with patch('shutil.copytree') as mock_copy:
         with patch('shutil.rmtree') as mock_rm:
             with patch('pathlib.Path.exists', return_value=False): # Destination doesn't exist
                 
                 result = generator.save_project(project_name)
                 
                 expected_dst = generator.output_root / project_name / "capcut_draft"
                 assert result == expected_dst
                 expected_dst = generator.output_root / project_name / "capcut_draft"
                 assert result == expected_dst
                 mock_copy.assert_called_with(mock_src, expected_dst)

def test_version_sync(generator):
    """Test that version info is synced from template."""
    # Mock template content
    template_data = {
        "new_version": "99.0.0",
        "version": 12345,
        "platform": {"app_version": "8.8.8"},
        "last_modified_platform": {"app_version": "8.8.8"}
    }
    
    # Mock script with content dict
    mock_script = MagicMock()
    mock_script.content = {}
    generator.folder.create_draft.return_value = mock_script
    
    # Mock file existence and reading
    with patch("pathlib.Path.exists", return_value=True), \
         patch("builtins.open", new_callable=MagicMock) as mock_open, \
         patch("json.load", return_value=template_data):
         
         generator._initialize_script("TestProject")
         
         # Verify updates
         assert mock_script.content['new_version'] == "99.0.0"
         assert mock_script.content['version'] == 12345
         assert mock_script.content['platform']['app_version'] == "8.8.8"
         assert mock_script.content['last_modified_platform']['app_version'] == "8.8.8"
         mock_script.save.assert_called()
