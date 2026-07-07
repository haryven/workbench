import sys
import re

def process_message(content):
    lines = content.splitlines()
    if not lines:
        return content

    # 1. Subject Fix
    subject = lines[0].strip()
    if subject.startswith("OPENEULER: "):
        subject = subject[11:]
        
    # Unified conversion: ub:xxx, ub: xxx, ub/xxx -> ub/xxx:
    match = re.match(r'^ub[:/]\s*([\w-]+)[:\s]*(.*)', subject, re.IGNORECASE)
    if match:
        subsystem = match.group(1)
        rest = match.group(2).strip()
        
        # Remove redundant prefix (e.g., ub/hisi-ubus: ub:hisi-ubus:)
        redundant_pattern = rf'^ub[:/]\s*{re.escape(subsystem)}[:\s]*(.*)'
        while True:
            sub_match = re.match(redundant_pattern, rest, re.IGNORECASE)
            if sub_match:
                rest = sub_match.group(1).strip()
            else:
                break
        subject = f"ub/{subsystem}: {rest}"
    
    subject = f"OPENEULER: {subject}"

    # 2. Filter Body Content
    # We need to extract the "real" body content, ignoring metadata we might have added previously
    # and ignoring signatures/footers we want to re-position.
    
    generated_headers = [
        "Mainline: KYLIN-only",
        "Severity: Moderate",
        "Task: #596319"
    ]
    
    remove_signatures = [
        "K2CI-Arch: Arm64",
        "Signed-off-by: Huiwen He <hehuiwen@kylinos.cn>"
    ]

    cleaned_body = []
    change_id_line = ""
    link_line = ""
    
    # Start scanning from line 1
    # We look for the separator '---' just in case (old format)
    separator_index = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('-' * 20):
            separator_index = i
            break
            
    # If separator found, we only take content after it (old format logic)
    # But we also scan before it for bugzilla (old format logic)
    scan_range = lines[1:]
    start_index = 1
    
    if separator_index != -1:
        # Check bugzilla before separator
        for line in lines[:separator_index]:
            if 'bugzilla:' in line.lower():
                parts = line.split(':', 1)
                if len(parts) > 1:
                    link_line = f"Link: {parts[1].strip()}"
                break
        start_index = separator_index + 1
        
    for line in lines[start_index:]:
        stripped = line.strip()
        
        # Skip generated headers (from previous run)
        if stripped in generated_headers:
            continue
            
        # Extract Change-Id
        if stripped.lower().startswith("change-id:"):
            change_id_line = stripped
            continue
            
        # Extract Link (if already present in new format)
        if stripped.startswith("Link:"):
            link_line = stripped
            continue
            
        # Fallback Extract Bugzilla (if present in body of old format without separator? Unlikely but safe)
        if 'bugzilla:' in stripped.lower() and not link_line:
             parts = stripped.split(':', 1)
             if len(parts) > 1:
                 link_line = f"Link: {parts[1].strip()}"
             continue

        # Skip signatures to remove
        if stripped in remove_signatures:
            continue
            
        cleaned_body.append(line)

    # Trim empty lines from start/end of extracted body
    while cleaned_body and not cleaned_body[0].strip():
        cleaned_body.pop(0)
    while cleaned_body and not cleaned_body[-1].strip():
        cleaned_body.pop()

    body_text = "\n".join(cleaned_body)

    # 5. Construct New Message
    new_msg = []
    new_msg.append(subject)
    new_msg.append("")
    new_msg.append("Mainline: KYLIN-only")
    new_msg.append("Severity: Low")
    new_msg.append("")
    new_msg.append("Task: #596319")
    new_msg.append("")
    new_msg.append(body_text)
    new_msg.append("")
    
    if link_line:
        new_msg.append(link_line)
        
    if change_id_line:
        new_msg.append(change_id_line)
    
    new_msg.append("Signed-off-by: Huiwen He <hehuiwen@kylinos.cn>")
    
    return "\n".join(new_msg)

if __name__ == "__main__":
    try:
        with open('msg.txt', 'r', encoding='utf-8') as f:
            content = f.read()

        new_content = process_message(content)

        with open('msg.txt', 'w', encoding='utf-8') as f:
            f.write(new_content)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
