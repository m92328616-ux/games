import os
import time
from collections import defaultdict

def parse_and_animate_horde(file_path, fps=2):
    """
    Parses the custom .dat file format, groups pairs of lines into 5 characters,
    stacks them vertically, and animates them bouncing back and forth across the screen.
    """
    frame_data = defaultdict(list)
    
    # 1. Parse the file and group matching lines by their frame prefix
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            stripped_line = line.rstrip('\r\n')
            if not stripped_line:
                continue
                
            prefix = stripped_line[:3]
            
            if prefix.isdigit():
                artwork_line = stripped_line[3:]
                frame_data[prefix].append(artwork_line)

    # Define our 5 characters and their two alternating animation steps
    character_pairs = [
        ("001", "002"),  # Character 1
        ("003", "004"),  # Character 2
        ("005", "006"),  # Character 3
        ("007", "008"),  # Character 4
        ("009", "010")   # Character 5
    ]

    # Verify all required frames exist in your file data
    for first, second in character_pairs:
        if first not in frame_data or second not in frame_data:
            print(f"Error: Missing frames {first} or {second} in your data file.")
            return

    # 2. Setup timing and movement settings
    clear_command = 'cls' if os.name == 'nt' else 'clear'
    delay = 1.0 / fps
    
    x_pos = 0        # Starting horizontal position
    direction = 1    # 1 means moving right, -1 means moving left
    step_toggle = 0  # Cycles between 0 and 1 to switch animation frames

    print("Starting bouncing vertical stack animation...")
    print("Press Ctrl+C to stop...")
    time.sleep(1.0)

    # 3. Main animation loop
    try:
        while True:
            # Clear the terminal screen
            os.system(clear_command)
            
            # Create our horizontal shift padding
            padding = " " * x_pos
            
            # This list will hold all lines of the combined vertical artwork stack
            combined_display_lines = []
            
            # Build the vertical layout by pulling the active step for each character
            for first, second in character_pairs:
                # Alternate between the first and second frame token
                active_frame_id = first if step_toggle == 0 else second
                
                # Prepend horizontal padding to each individual line of the character
                for line in frame_data[active_frame_id]:
                    combined_display_lines.append(f"{padding}{line}")
                
                # Add a blank line spacing between characters to separate them cleanly
                combined_display_lines.append("")

            # Print out the stacked frames
            print("\n".join(combined_display_lines))
            
            # Update position based on the current direction (moves right if 1, moves left if -1)
            x_pos += 2 * direction
            step_toggle = 1 - step_toggle  # Toggle walking frame
            
            # 4. Check boundaries and bounce
            # Turn left if hitting the right boundary
            if x_pos >= 60:
                x_pos = 60
                direction = -1
            # Turn right if hitting the left boundary
            elif x_pos <= 0:
                x_pos = 0
                direction = 1
                
            time.sleep(delay)
            
    except KeyboardInterrupt:
        os.system(clear_command)
        print("Animation stopped.")

if __name__ == "__main__":
    # Get the directory where spaceinvaders.py sits
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Point directly to your active data file name
    file_name = os.path.join(script_dir, "ASCINV.DAT")
    
    # Run the main engine loop
    parse_and_animate_horde(file_name, fps=2)
