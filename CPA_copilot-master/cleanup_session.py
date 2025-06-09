"""
CPA Copilot Session Cleanup Script
Fixes session state management and cleans up old files.
"""

import os
import shutil
from pathlib import Path
import json
from datetime import datetime, timedelta

def clean_upload_directory(upload_path: str, keep_recent_hours: int = 2):
    """
    Clean the upload directory of old files.
    
    Args:
        upload_path: Path to the uploads directory
        keep_recent_hours: Keep files modified within this many hours
    """
    upload_dir = Path(upload_path)
    if not upload_dir.exists():
        print(f"Upload directory does not exist: {upload_path}")
        return
    
    cutoff_time = datetime.now() - timedelta(hours=keep_recent_hours)
    files_removed = 0
    
    print(f"Cleaning upload directory: {upload_dir}")
    print(f"Removing files older than {keep_recent_hours} hours...")
    
    for file_path in upload_dir.glob("*"):
        if file_path.is_file():
            # Get file modification time
            mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            if mod_time < cutoff_time:
                print(f"  Removing old file: {file_path.name}")
                file_path.unlink()
                files_removed += 1
            else:
                print(f"  Keeping recent file: {file_path.name}")
    
    print(f"Cleanup complete. Removed {files_removed} old files.")

def clean_workpaper_directory(workpaper_path: str, keep_recent_days: int = 7):
    """
    Clean the workpaper directory of old files.
    
    Args:
        workpaper_path: Path to the workpapers directory
        keep_recent_days: Keep files modified within this many days
    """
    workpaper_dir = Path(workpaper_path)
    if not workpaper_dir.exists():
        print(f"Workpaper directory does not exist: {workpaper_path}")
        return
    
    cutoff_time = datetime.now() - timedelta(days=keep_recent_days)
    files_removed = 0
    
    print(f"Cleaning workpaper directory: {workpaper_dir}")
    print(f"Removing files older than {keep_recent_days} days...")
    
    for file_path in workpaper_dir.glob("*.pdf"):
        if file_path.is_file():
            # Get file modification time
            mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            if mod_time < cutoff_time:
                print(f"  Removing old workpaper: {file_path.name}")
                file_path.unlink()
                files_removed += 1
            else:
                print(f"  Keeping recent workpaper: {file_path.name}")
    
    print(f"Workpaper cleanup complete. Removed {files_removed} old files.")

def reset_session_state():
    """
    Instructions for resetting session state in Streamlit.
    """
    print("""
SESSION STATE RESET INSTRUCTIONS

To properly reset the session state in your Streamlit app:

1. **In the Upload tab**: Click "Clear All" to remove uploaded files
2. **Restart the Streamlit app**: 
   - Press Ctrl+C in the terminal
   - Run: streamlit run frontend/streamlit/app.py
3. **Or add this to your app.py** for a reset button:

```python
# Add this to your sidebar
if st.sidebar.button("Reset Everything"):
    # Clear session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    # Clean upload files
    clean_upload_directory("temp/uploads")
    
    st.success("Session reset! Please refresh the page.")
    st.rerun()
```

4. **Current session state keys to clear**:
   - uploaded_files
   - processing_batch
   - processed_documents
   - workpaper_path
   - agent
   - chat_history
""")

def run_comprehensive_cleanup():
    """
    Run a comprehensive cleanup of the CPA Copilot project.
    """
    print("Starting CPA Copilot Comprehensive Cleanup...")
    print("=" * 50)
    
    # Define paths
    base_path = Path(".")
    upload_path = base_path / "temp" / "uploads"
    workpaper_path = base_path / "temp" / "workpapers"
    
    # Clean uploads (keep files from last 2 hours)
    clean_upload_directory(str(upload_path), keep_recent_hours=2)
    print()
    
    # Clean workpapers (keep files from last 7 days)
    clean_workpaper_directory(str(workpaper_path), keep_recent_days=7)
    print()
    
    # Session state instructions
    reset_session_state()
    
    print("=" * 50)
    print("Cleanup complete!")
    print("\nNEXT STEPS:")
    print("1. Restart your Streamlit app")
    print("2. Upload ONLY your current 3 documents:")
    print("   - TAX-1099-INT.png")
    print("   - TAX-1098-E.png") 
    print("   - TAX-1098-T.png")
    print("3. Process the documents")
    print("4. Test the income calculation with: 'What is my total income?'")
    print("\nEXPECTED RESULT:")
    print("The AI should now correctly calculate $123,456 from your 1099-INT!")

if __name__ == "__main__":
    run_comprehensive_cleanup()
