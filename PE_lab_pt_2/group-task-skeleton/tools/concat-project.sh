#!/bin/bash

# Script to concatenate project files into a single text file,
# preserving relative paths and ignoring specified directories/files.

# --- Configuration ---
# Add other common virtual environment names if needed
VENV_NAMES=("venv" ".venv" "env" ".env" "env.bak" "venv.bak")
# Add other directory names to ignore
IGNORE_DIRS=("build")

# --- Argument Handling ---
if [[ "$#" -ne 2 ]]; then
  echo "Usage: $0 <project_type> <output_filename>"
  echo "  project_type: 'python' or 'frontend'"
  echo "  output_filename: The name of the file to create"
  exit 1
fi

PROJECT_TYPE="$1"
OUTPUT_FILE="$2"

# Validate project type
if [[ "$PROJECT_TYPE" != "python" && "$PROJECT_TYPE" != "frontend" ]]; then
  echo "Error: Invalid project type '$PROJECT_TYPE'. Must be 'python' or 'frontend'."
  exit 1
fi

# --- Prepare Output File ---
# Clear the output file if it exists, or create it if it doesn't
> "$OUTPUT_FILE"
echo "Starting project concatenation..."
echo "Output will be saved to: $OUTPUT_FILE"
echo "Project type: $PROJECT_TYPE"

# --- Build Find Command ---

# Base find command starts in the current directory (.)
FIND_CMD="find ."

# 1. Ignore patterns (hidden files/dirs, virtual envs, and specific dirs)
# Start group for ignore paths
FIND_CMD+=" \( "
# Ignore hidden files and directories (starting with .)
FIND_CMD+=" -path '*/.*' "
# Ignore specified virtual environment directories
for venv_name in "${VENV_NAMES[@]}"; do
  FIND_CMD+=" -o -path '*/$venv_name' "
done
# Ignore other specified directories (like 'build')
for ignore_dir in "${IGNORE_DIRS[@]}"; do
  FIND_CMD+=" -o -path '*/$ignore_dir' " # <<< Added this loop
done
# End group and prune matching paths (don't descend into them)
FIND_CMD+=" \) -prune -o"

# 2. Select file types based on project type
# Start group for file types
FIND_CMD+=" \( "
if [[ "$PROJECT_TYPE" == "python" ]]; then
  FIND_CMD+=" -name '*.py' -o -name '*.toml' "
  echo "Including: .py, .toml files"
elif [[ "$PROJECT_TYPE" == "frontend" ]]; then
  FIND_CMD+=" -name '*.html' -o -name '*.css' -o -name '*.js' "
  echo "Including: .html, .css, .js files"
fi
# End group for file types
FIND_CMD+=" \)"

# 3. Ensure we only process actual files (-type f)
FIND_CMD+=" -type f"

# 4. Action: Print null-delimited filenames for safe handling
FIND_CMD+=" -print0"

echo "----------------------------------------"
# --- Execute Find and Process Files ---
# Use process substitution and a while loop to read null-delimited filenames
# This is robust for filenames containing spaces or special characters.
processed_count=0
while IFS= read -r -d $'\0' file; do
  # Remove the leading './' from the find output for cleaner relative paths
  relative_path="${file#./}"

  echo "Processing: $relative_path"

  # Append header with relative path to the output file
  echo "--- START FILE: $relative_path ---" >> "$OUTPUT_FILE"

  # Append file content to the output file
  cat "$file" >> "$OUTPUT_FILE"

  # Append footer and blank lines for readability
  echo "" >> "$OUTPUT_FILE" # Add a newline after content
  echo "--- END FILE: $relative_path ---" >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE" # Add a blank line between files
  echo "" >> "$OUTPUT_FILE" # Add another blank line

  ((processed_count++))

done < <(eval $FIND_CMD) # Use eval to correctly interpret the constructed find command string

echo "----------------------------------------"
echo "Concatenation complete."
echo "Processed $processed_count file(s)."
echo "Result saved to: $OUTPUT_FILE"

exit 0