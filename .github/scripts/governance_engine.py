import os
import yaml
import requests
import shutil
import subprocess
import re
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION & CONSTANTS ---
# Standard Time Offset: IST (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("GITHUB_REPOSITORY")  # Expected format: "owner/repo"
CANONICAL_REPO = "Garudex-Labs/scm" # Fork protection target to prevent unauthorized syncs

# Directory and File Paths
REGISTRY_PATH = "governance/contributors.yaml"
BOTS_PATH = "governance/bots.yaml"
HISTORY_DIR = "governance/history/users/"
HISTORY_BOTS_DIR = "governance/history/bots/"
LEDGER_PATH = "governance/history/ledger.yaml"
BOT_LEDGER_PATH = "governance/history/bot_logs.yaml"
CODEOWNERS_PATH = ".github/CODEOWNERS"

# Role Progression System (Lower index equates to junior role)
ROLE_HIERARCHY = [
    "Newbie Contributor",
    "Active Contributor",
    "Core Contributor",
    "Principal Contributor",
    "Maintainer"
]

# Exclusive roles possessing supreme repository privileges
PROTECTED_ROLES = ["OWNER"]

# API Request Headers
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def get_authorized_users():
    """
    Parses the .github/CODEOWNERS file to identify personnel authorized 
    to approve governance modifications and role assignments.
    """
    if not os.path.exists(CODEOWNERS_PATH):
        print(f"[WARNING] Code owners configuration not found at {CODEOWNERS_PATH}.")
        return []
    
    authorized = set()
    try:
        with open(CODEOWNERS_PATH, 'r') as f:
            for line in f:
                # Isolate lines governing the primary registry file
                if line.strip().startswith("governance/contributors.yaml"):
                    parts = line.split()
                    for part in parts:
                        if part.startswith('@'):
                            authorized.add(part.lstrip('@').lower())
    except Exception as e:
        print(f"[ERROR] Failed to parse CODEOWNERS file: {e}")
    
    return list(authorized)

def validate_role_change(action, current_role, target_role):
    """
    Evaluates requested role modifications against the established hierarchy 
    to determine the validity of a promotion or demotion.
    Returns a tuple: (is_valid: bool, error_message: str|None)
    """
    if target_role not in ROLE_HIERARCHY:
        return False, f"Role '{target_role}' is not recognized within the official governance hierarchy."
    
    if current_role in PROTECTED_ROLES:
        return False, f"Role '{current_role}' represents a supreme repository privilege and cannot be modified via automated commands."
    
    # Handle legacy or non-standard roles outside the standard progression hierarchy
    if current_role not in ROLE_HIERARCHY:
        current_idx = -1 
    else:
        current_idx = ROLE_HIERARCHY.index(current_role)
    
    target_idx = ROLE_HIERARCHY.index(target_role)

    if action == "promote":
        if target_idx <= current_idx:
            return False, f"Invalid promotion parameter: Cannot transition to '{target_role}' from '{current_role}' as the target tier is not senior."
    elif action == "demote":
        if target_idx >= current_idx and current_idx != -1:
            return False, f"Invalid demotion parameter: Cannot transition to '{target_role}' from '{current_role}' as the target tier is not junior."
    
    return True, None

def get_now_ist_str():
    """Generates the current timestamp formatted in IST (ISO 8601 standard)."""
    return datetime.now(IST).strftime("%Y-%m-%dT%H:%M:%S+05:30")

def get_merged_prs(since_date=None, per_page=100):
    """
    Retrieves merged pull requests from the GitHub API. 
    If a since_date parameter is provided, the query is restricted to PRs merged after that timestamp.
    """
    all_prs = []
    page = 1
    
    since_dt = None
    if since_date:
        try:
            since_dt = datetime.fromisoformat(since_date)
        except ValueError:
            print(f"[WARNING] Unrecognized timestamp format for since_date '{since_date}'. Reverting to full historical fetch.")
            since_dt = None

    sync_scope = f"since {since_date}" if since_date else "FULL HISTORICAL FETCH"
    print(f"[INFO] Initiating pull request retrieval protocol ({sync_scope})...")

    while True:
        # Retrieve closed pull requests, prioritized by recent updates
        url = f"https://api.github.com/repos/{REPO}/pulls?state=closed&sort=updated&direction=desc&per_page={per_page}&page={page}"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            pulls = response.json()
            
            if not pulls:
                break
                
            relevant_prs_in_batch = 0
            
            for pr in pulls:
                if not pr.get('merged_at'):
                    continue
                
                merged_at_str = pr['merged_at']
                merged_at_dt = datetime.fromisoformat(merged_at_str.replace('Z', '+00:00'))
                
                # Apply date filtration bounds
                if since_dt and merged_at_dt <= since_dt:
                    continue
                
                all_prs.append({
                    'username': pr['user']['login'],
                    'merged_at': pr['merged_at'],
                    'url': pr['html_url'],
                    'title': pr['title'],
                    'number': pr['number']
                })
                relevant_prs_in_batch += 1
            
            print(f"[INFO] Processed pagination index {page}: Identified {relevant_prs_in_batch} qualifying merged PRs.")
            
            if not pulls:
                break
                
            page += 1
            # Implement a safe pagination limit to prevent API exhaustion during incremental synchronization
            if page > 50 and since_dt:
                 print("[INFO] Pagination threshold reached for incremental synchronization. Halting retrieval.")
                 break
            
        except Exception as e:
            print(f"[ERROR] API failure encountered during pagination index {page} fetch: {e}")
            break
            
    return all_prs

def get_last_activity_date(username):
    """Queries the GitHub Events API to ascertain the timestamp of a user's most recent public action."""
    url = f"https://api.github.com/users/{username}/events/public"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            events = response.json()
            if events and isinstance(events, list):
                return events[0]['created_at'].split('T')[0]
    except Exception as e:
        print(f"[ERROR] Failed to verify recent activity for user {username}: {e}")
    return None

def update_user_history(username, event_type, details, is_bot=False):
    """Maintains an immutable, append-only chronological audit log for individual entities."""
    base_dir = HISTORY_BOTS_DIR if is_bot else HISTORY_DIR
    os.makedirs(base_dir, exist_ok=True)
    
    # Enforce lowercase filenames to prevent case-sensitivity conflicts across environments
    path = os.path.join(base_dir, f"{username.lower()}.yaml")
    
    data = {"username": username, "events": []}
    if os.path.exists(path):
        with open(path, 'r') as f:
            existing_data = yaml.safe_load(f)
            if existing_data:
                data = existing_data

    # Append standard event structure
    new_event = {
        "timestamp": get_now_ist_str(),
        "type": event_type,
        "details": details
    }
    
    data['events'].append(new_event)

    with open(path, 'w') as f:
        yaml.dump(data, f, sort_keys=False, default_flow_style=False)

def update_ledger(event_type, username, details, is_bot=False):
    """Maintains a unified, global ledger encompassing all governance operations."""
    ledger_file = BOT_LEDGER_PATH if is_bot else LEDGER_PATH
    os.makedirs(os.path.dirname(ledger_file), exist_ok=True)
    
    data = {"events": []}
    if os.path.exists(ledger_file) and os.path.getsize(ledger_file) > 0:
        with open(ledger_file, 'r') as f:
            existing_data = yaml.safe_load(f)
            if existing_data and 'events' in existing_data:
                data = existing_data
    
    data['events'].append({
        "timestamp": get_now_ist_str(),
        "type": event_type,
        "username": username,
        "details": details
    })
    
    with open(ledger_file, 'w') as f:
        yaml.dump(data, f, sort_keys=False, default_flow_style=False)

def post_comment(issue_number, body):
    """Transmits a formal status or error message directly to the Pull Request or Issue thread."""
    url = f"https://api.github.com/repos/{REPO}/issues/{issue_number}/comments"
    try:
        requests.post(url, json={"body": body}, headers=headers).raise_for_status()
    except Exception as e:
        print(f"[ERROR] Comment transmission failed: {e}")

def git_commit_push_pr(pr_number, branch_name):
    """Executes version control operations to stage, commit, and push modifications to the active branch."""
    try:
        # Initialize Git Configuration
        subprocess.run(["git", "config", "--local", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--local", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], check=True)
        
        # Stage registry modifications
        subprocess.run(["git", "add", "governance/"], check=True)
        
        # Verify pending changes prior to commit execution
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if not status.stdout.strip():
            print("[INFO] No file modifications detected. Bypassing commit sequence.")
            return

        # Execute Commit
        msg = f"chore(gov): execute role update command via PR #{pr_number} [skip ci]"
        subprocess.run(["git", "commit", "-s", "-m", msg], check=True)
        
        subprocess.run(["git", "pull", "origin", branch_name, "--rebase"], check=True)

        # Transmit to Remote
        subprocess.run(["git", "push", "origin", f"HEAD:{branch_name}"], check=True)
        
    except Exception as e:
        print(f"[CRITICAL] Git operation failure: {e}")
        raise e

def load_bots():
    """Retrieves the list of registered automation accounts."""
    if not os.path.exists(BOTS_PATH):
        return []
    with open(BOTS_PATH, 'r') as f:
        data = yaml.safe_load(f)
        return data.get('bots', []) if data else []

def save_bots(bots_list):
    """Persists the updated list of automation accounts to the file system."""
    os.makedirs(os.path.dirname(BOTS_PATH), exist_ok=True)
    data = {'bots': bots_list}
    with open(BOTS_PATH, 'w') as f:
        yaml.dump(data, f, sort_keys=False, default_flow_style=False)

def move_ledger_entries(username, source_path, dest_path):
    """Transfers historical ledger entries for a specified user between distinct administrative ledgers."""
    if not os.path.exists(source_path):
        return

    # Ingest Source Ledger
    try:
        with open(source_path, 'r') as f:
            src_data = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"[ERROR] Failed to load source ledger at {source_path}: {e}")
        return
    
    src_events = src_data.get('events', [])
    if not src_events:
        return

    # Ingest Destination Ledger
    dest_data = {'events': []}
    if os.path.exists(dest_path):
        try:
            with open(dest_path, 'r') as f:
                loaded = yaml.safe_load(f)
                if loaded:
                    dest_data = loaded
        except Exception as e:
             print(f"[ERROR] Failed to load destination ledger at {dest_path}: {e}")
    
    if 'events' not in dest_data:
        dest_data['events'] = []

    # Segregate Events for Transfer
    events_to_keep = []
    events_to_move = []
    
    username_lower = username.lower()
    
    for event in src_events:
        if event.get('username', '').lower() == username_lower:
            events_to_move.append(event)
        else:
            events_to_keep.append(event)
            
    if not events_to_move:
        return # Bypass if no matching events are found

    # Apply Transfer
    src_data['events'] = events_to_keep
    
    # Consolidate and sort destination events chronologically
    combined_events = dest_data['events'] + events_to_move
    combined_events.sort(key=lambda x: x.get('timestamp', ''))
    dest_data['events'] = combined_events
    
    # Persist modifications to disk
    try:
        with open(source_path, 'w') as f:
            yaml.dump(src_data, f, sort_keys=False, default_flow_style=False)

        with open(dest_path, 'w') as f:
            yaml.dump(dest_data, f, sort_keys=False, default_flow_style=False)
        print(f"[INFO] Successfully migrated {len(events_to_move)} historical events from {source_path} to {dest_path}.")
    except Exception as e:
        print(f"[ERROR] Failed to persist modified ledgers to disk: {e}")

def handle_bot_command(action, target_user, author, pr_number, branch_name):
    """Processes directives related to the tracking and classification of automation accounts."""
    print(f"[INFO] Executing Administrative Command: {action} {target_user} authorized by {author}")
    
    # Ingest system registries
    with open(REGISTRY_PATH, 'r') as f:
        registry = yaml.safe_load(f)
    contributors = registry.get('contributors', [])
    
    bots = load_bots()
    target_user_lower = target_user.lower()
    
    if action == "add":
        # Validate existing classification
        if any(b['username'].lower() == target_user_lower for b in bots):
            post_comment(pr_number, f"[NOTICE] Target user @{target_user} is already classified within the automation registry.")
            return

        # Address potential pre-existing human contributor status (Migration Protocol)
        user_entry = next((c for c in contributors if c['username'].lower() == target_user_lower), None)
        if user_entry:
            contributors.remove(user_entry)
            # Persist registry immediately to reflect removal
            with open(REGISTRY_PATH, 'w') as f:
                yaml.dump(registry, f, sort_keys=False, default_flow_style=False)
                
            # Execute physical history migration
            src = os.path.join(HISTORY_DIR, f"{target_user_lower}.yaml")
            dst = os.path.join(HISTORY_BOTS_DIR, f"{target_user_lower}.yaml")
            if os.path.exists(src):
                os.makedirs(HISTORY_BOTS_DIR, exist_ok=True)
                shutil.move(src, dst)
        
        # Instantiate new bot profile
        new_bot = {
            "username": target_user,
            "added_at": get_now_ist_str(),
            "added_by": author
        }
        bots.append(new_bot)
        save_bots(bots)
        
        # Execute Ledger Migration
        move_ledger_entries(target_user, LEDGER_PATH, BOT_LEDGER_PATH)
        
        # Log administrative action to the primary governance ledger
        log_msg = f"Registered @{target_user} to automation tracking (migrated from contributors if applicable) authorized by @{author}"
        update_ledger("BOT_ADD", target_user, log_msg, is_bot=False) 
        post_comment(pr_number, f"[SUCCESS] User @{target_user} has been successfully added to the automation registry.")

    elif action == "remove":
        # Validate existing classification
        bot_entry = next((b for b in bots if b['username'].lower() == target_user_lower), None)
        if not bot_entry:
            post_comment(pr_number, f"[NOTICE] Target user @{target_user} does not currently exist within the automation registry.")
            return
            
        bots.remove(bot_entry)
        save_bots(bots)
        
        # Execute reverse physical history migration
        src = os.path.join(HISTORY_BOTS_DIR, f"{target_user_lower}.yaml")
        dst = os.path.join(HISTORY_DIR, f"{target_user_lower}.yaml")
        if os.path.exists(src):
            os.makedirs(HISTORY_DIR, exist_ok=True)
            shutil.move(src, dst)

        # Execute reverse Ledger Migration
        move_ledger_entries(target_user, BOT_LEDGER_PATH, LEDGER_PATH)

        # Reinstate Contributor Status (Defaults to Newbie)
        if not any(c['username'].lower() == target_user_lower for c in contributors):
            new_contributor = {
                "username": target_user,
                "role": "Newbie Contributor",
                "team": "Repository",
                "status": "active",
                "assigned_by": author,
                "assigned_at": get_now_ist_str(),
                "last_activity": get_now_ist_str(), 
                "notes": "Restored status from automation tracking."
            }
            contributors.append(new_contributor)
            with open(REGISTRY_PATH, 'w') as f:
                yaml.dump(registry, f, sort_keys=False, default_flow_style=False)

        # Log administrative action to the primary governance ledger
        log_msg = f"Removed @{target_user} from automation tracking authorized by @{author}"
        update_ledger("BOT_REMOVE", target_user, log_msg, is_bot=False)
        post_comment(pr_number, f"[SUCCESS] User @{target_user} has been successfully removed from the automation registry.")
        
    # Finalize Transaction
    try:
        git_commit_push_pr(pr_number, branch_name)
    except Exception as e:
        post_comment(pr_number, f"[WARNING] Registry modifications were applied locally but failed to synchronize with the remote branch: {str(e)}")

def run_command_mode(event_path, event_name):
    """Primary execution pathway for interactive governance commands originating from issue/PR comments."""
    import json
    
    if not os.path.exists(event_path):
        print("[ERROR] GitHub event payload path not found.")
        return

    with open(event_path, 'r') as f:
        event = json.load(f)
    
    # Extract payload metadata
    if event_name == 'issue_comment':
        comment = event.get('comment', {})
        body = comment.get('body', '')
        author = comment.get('user', {}).get('login')
        pr_number = event.get('issue', {}).get('number')
    else:
        print(f"[ERROR] Unsupported event trigger utilized for interactive commands: {event_name}")
        return

    # Enforce Authorization Hierarchy
    authorized_users = get_authorized_users()
    if author.lower() not in authorized_users:
        if "/gov" in body:
             post_comment(pr_number, f"[DENIED] Authorization Failure: User @{author} is not a recognized Maintainer or Principal assigned to governance oversight.")
        return

    # Resolve Contextual Branch and Align Repository State
    try:
        if event_name == 'pull_request':
            branch_name = event['pull_request']['head']['ref']
        else:
            # Query GitHub API to resolve branch origin for comment events
            pr_url = event['issue']['pull_request']['url']
            pr_data = requests.get(pr_url, headers=headers).json()
            branch_name = pr_data['head']['ref']
            
        print(f"[INFO] Aligning state with contextual branch: {branch_name}")
        subprocess.run(["git", "fetch", "origin", branch_name], check=True)
        subprocess.run(["git", "checkout", branch_name], check=True)
    except Exception as e:
        post_comment(pr_number, f"[ERROR] System failed to resolve or checkout the requested branch: {str(e)}")
        return

    # Command Signature Matching Rules
    # Pattern 1: Role Modification (/gov promote @user "Role Name")
    pattern_role = r'^\s*\/gov\s+(promote|demote)\s+@([a-zA-Z0-9-]+)\s+"([^"]+)"'
    # Pattern 2: Automation Tracking (/gov bot add @user)
    pattern_bot = r'^\s*\/gov\s+bot\s+(add|remove)\s+@([a-zA-Z0-9\[\]-]+)'

    match_role = re.search(pattern_role, body, re.MULTILINE)
    match_bot = re.search(pattern_bot, body, re.MULTILINE)

    if match_bot:
        action, target_user = match_bot.groups()
        handle_bot_command(action, target_user, author, pr_number, branch_name)
        return

    if match_role:
        action, target_user, target_role = match_role.groups()
        
        # Restrict operations on known automation accounts
        bots = load_bots()
        if any(b['username'].lower() == target_user.lower() for b in bots):
             post_comment(pr_number, f"[DENIED] Operation Rejected: User @{target_user} is classified as an automated service. Governance roles apply exclusively to human contributors.")
             return

        # Execute Role Modification Logic
        with open(REGISTRY_PATH, 'r') as f:
            registry = yaml.safe_load(f)
        
        contributors = registry.get('contributors', [])
        target_entry = next((c for c in contributors if c['username'].lower() == target_user.lower()), None)
        
        if not target_entry:
            post_comment(pr_number, f"[ERROR] Record missing: User @{target_user} does not currently exist within the official governance registry.")
            return

        current_role = target_entry.get('role', 'Newbie Contributor')
        is_valid, err = validate_role_change(action, current_role, target_role)
        
        if not is_valid:
            post_comment(pr_number, f"[ERROR] Policy violation: {err}")
            return

        # Commit State Modifications
        target_entry['role'] = target_role
        target_entry['assigned_at'] = get_now_ist_str()
        target_entry['assigned_by'] = author
        
        with open(REGISTRY_PATH, 'w') as f:
            yaml.dump(registry, f, sort_keys=False, default_flow_style=False)
        
        # Log Audit Trail
        log_msg = f"Role formally adjusted from '{current_role}' to '{target_role}' authorized by @{author} via Pull Request #{pr_number}"
        update_user_history(target_user, "ROLE_CHANGE", log_msg, is_bot=False)
        update_ledger("ROLE_CHANGE", target_user, log_msg, is_bot=False)
        
        # Finalize and Push to Remote
        try:
            git_commit_push_pr(pr_number, branch_name)
            post_comment(pr_number, f"[SUCCESS] Governance records formally updated: @{target_user} has been granted the title of **{target_role}**.")
        except Exception as e:
            post_comment(pr_number, f"[WARNING] Role modification was logged locally but failed to propagate to the remote branch: {str(e)}")

def main():
    """Primary routing protocol determining script execution mode based on GitHub event context."""
    event_name = os.getenv("GITHUB_EVENT_NAME")
    event_path = os.getenv("GITHUB_EVENT_PATH")
    
    if event_name == 'issue_comment':
        run_command_mode(event_path, event_name)
        
    elif event_name == 'pull_request':
        import json
        with open(event_path, 'r') as f:
            event = json.load(f)
        if event.get('pull_request', {}).get('merged'):
            run_sync_mode()
    else:
        run_sync_mode()

def run_sync_mode():
    """Maintains automated synchronization of contributor activity and governance metrics."""
    # --- FORK PROTECTION ENFORCEMENT ---
    if REPO != CANONICAL_REPO:
        print(f"[NOTICE] Bypassing governance synchronization: Current repository '{REPO}' operates independently from the canonical target '{CANONICAL_REPO}'.")
        return

    if not os.path.exists(REGISTRY_PATH):
        print(f"[CRITICAL] Missing Core System File: Registry not found at established path {REGISTRY_PATH}")
        return

    with open(REGISTRY_PATH, 'r') as f:
        registry = yaml.safe_load(f)

    contributors = registry.get('contributors', [])
    # Normalize usernames for environment-agnostic evaluation
    existing_usernames = {c['username'].lower() for c in contributors}
    
    # Ingest Automation Accounts
    bots = load_bots()
    bot_usernames = {b['username'].lower() for b in bots}
    
    # Evaluate Temporal Metadata
    if 'metadata' not in registry:
        registry['metadata'] = {}
    
    last_sync = registry['metadata'].get('last_sync')
    
    # Determine Sync Paradigm
    clean_start = False
    if not last_sync:
        clean_start = True
        print("[INFO] No prior synchronization timestamp detected. Initiating full baseline synchronization.")
    elif not os.path.exists(HISTORY_DIR) or not os.listdir(HISTORY_DIR):
        clean_start = True
        print("[INFO] Historical architecture corrupted or absent. Forcing full baseline synchronization to rebuild ledgers.")
    
    # Execute Baseline Rebuild Sequence
    if clean_start:
        print("[INFO] Purging compromised or outdated historical directories...")
        if os.path.exists(HISTORY_DIR):
            shutil.rmtree(HISTORY_DIR)
        os.makedirs(HISTORY_DIR, exist_ok=True)
        
        # Ensure parity by rebuilding bot ledgers simultaneously
        if os.path.exists(HISTORY_BOTS_DIR):
            shutil.rmtree(HISTORY_BOTS_DIR)
        os.makedirs(HISTORY_BOTS_DIR, exist_ok=True)
        
        if os.path.exists(LEDGER_PATH):
            os.remove(LEDGER_PATH)
        if os.path.exists(BOT_LEDGER_PATH):
            os.remove(BOT_LEDGER_PATH)
            
        # Execute global fetch
        prs_to_process = get_merged_prs(since_date=None)
        
        # Re-initialize human contributor ledgers
        for contributor in contributors:
            username = contributor['username']
            update_user_history(
                username, 
                "ROLE_ASSIGNMENT",
                f"Assigned role: {contributor['role']} authorized by {contributor.get('assigned_by', 'system_migration')}",
                is_bot=False
            )
            update_ledger(
                "ROLE_ASSIGNMENT",
                username,
                f"Role: {contributor['role']}, Authorized by: {contributor.get('assigned_by', 'system_migration')}",
                is_bot=False
            )
        
        # Re-initialize bot ledgers
        for bot in bots:
            username = bot['username']
            update_user_history(
                username,
                "BOT_REGISTRATION",
                f"Automated service tracked within registry. Registered by: {bot.get('added_by', 'system_migration')}",
                is_bot=True
            )

    else:
        print(f"[INFO] Commencing INCREMENTAL SYNCHRONIZATION tracking changes since {last_sync}")
        prs_to_process = get_merged_prs(since_date=last_sync)

    # Execute Pipeline
    print(f"[INFO] Pipeline established for {len(prs_to_process)} Pull Requests.")
    # Standardize chronological order to ensure ledger integrity
    prs_to_process.sort(key=lambda x: x['merged_at'])

    for pr in prs_to_process:
        username = pr['username']
        merged_at = pr['merged_at']
        pr_url = pr['url']
        
        is_bot = username.lower() in bot_usernames
        
        if is_bot:
            # Divert bot activity exclusively to bot ledgers
            update_user_history(username, "PR_MERGED", f"Merged PR #{pr['number']}: {pr['title']} ({pr['url']})", is_bot=True)
            update_ledger("PR_MERGED", username, f"PR #{pr['number']}: {pr['title']}", is_bot=True)
            # Ensure bot accounts are excluded from human governance registries
            continue
        
        # Human Contributor Evaluation Protocol
        
        # 1. Onboarding Protocol Execution
        if username.lower() not in existing_usernames:
            print(f"[INFO] Discovery Phase: Unrecognized contributor detected - {username}")
            new_contributor = {
                "username": username,
                "role": "Newbie Contributor",
                "team": "Repository",
                "status": "active",
                "assigned_by": "Alfred",
                "assigned_at": merged_at,
                "last_activity": merged_at.split('T')[0],
                "notes": "Automatically integrated following first verified code merge."
            }
            contributors.append(new_contributor)
            existing_usernames.add(username.lower())
            
            update_user_history(username, "ONBOARDING", f"Achieved Newbie rank via verified code merge: {pr_url}", is_bot=False)
            update_ledger("ONBOARDING", username, f"Initial code merge recorded: {pr_url}", is_bot=False)
        
        # 2. General Ledger Update
        update_user_history(username, "PR_MERGED", f"Merged PR #{pr['number']}: {pr['title']} ({pr['url']})", is_bot=False)
        update_ledger("PR_MERGED", username, f"PR #{pr['number']}: {pr['title']}", is_bot=False)

    # 3. Global Activity Evaluation Protocol
    print("\n[INFO] Commencing global activity audit...")
    for entry in contributors:
        username = entry['username']
        # Fail-safe logic to skip miscategorized automation accounts
        if username.lower() in bot_usernames:
             continue
             
        last_act = get_last_activity_date(username)
        
        if last_act:
            old_activity = entry.get('last_activity')
            entry['last_activity'] = last_act
            
            if old_activity != last_act:
                update_user_history(username, "ACTIVITY_UPDATE", f"Temporal activity marker updated to {last_act}", is_bot=False)
            
            # 90-Day Policy Enforcement Check
            last_act_dt = datetime.strptime(last_act, "%Y-%m-%d")
            now_naive = datetime.now()
            diff = now_naive - last_act_dt
            
            if diff > timedelta(days=90):
                if entry.get('status') != "inactive":
                    entry['status'] = "inactive"
                    update_user_history(username, "STATUS_CHANGE", "Account suspended to inactive state citing prolonged inactivity (90+ Days).", is_bot=False)
                    update_ledger("STATUS_CHANGE", username, "Suspension applied (Inactivity)", is_bot=False)
            else:
                if entry.get('status') == "inactive":
                    entry['status'] = "active"
                    update_user_history(username, "STATUS_CHANGE", "Account restored to active standing due to detected participation.", is_bot=False)
                    update_ledger("STATUS_CHANGE", username, "Account restored (Renewed Activity)", is_bot=False)
    
    # 4. Metadata Stabilization
    registry['metadata']['last_sync'] = get_now_ist_str()
    registry['metadata']['total_contributors'] = len(contributors)
    registry['metadata']['active_contributors'] = sum(1 for c in contributors if c.get('status') == 'active')

    # Commit state to disk
    with open(REGISTRY_PATH, 'w') as f:
        yaml.dump(registry, f, sort_keys=False, default_flow_style=False)
    
    print("\n[SUCCESS] Governance synchronization protocols concluded normally.")
    print(f"[STATISTIC] Total personnel registered: {len(contributors)}")
    print(f"[STATISTIC] Currently active personnel: {registry['metadata']['active_contributors']}")

if __name__ == "__main__":
    main()