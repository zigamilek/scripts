#!/bin/bash

# =============================================================================
# Script Name: find_symlinks.sh
# Description: Finds and lists all symbolic links that point to each subfolder
#              within a specified target directory.
# Usage:       ./find_symlinks.sh /path/to/target_directory [search_directories...]
# Example:     ./find_symlinks.sh /var/www /home /etc
# =============================================================================

# ----------------------------
# Function to display usage
# ----------------------------
usage() {
    echo "Usage: $0 /path/to/target_directory [search_directories...]"
    echo "If no search directories are specified, the entire filesystem '/' is searched."
    exit 1
}

# ----------------------------
# Check for at least one argument
# ----------------------------
if [ $# -lt 1 ]; then
    echo "Error: Target directory not specified."
    usage
fi

# ----------------------------
# Variables
# ----------------------------
TARGET_DIR="$1"
shift  # Shift to access optional search directories

# If additional arguments are provided, use them as search paths
# Otherwise, default to searching the entire filesystem
if [ $# -ge 1 ]; then
    SEARCH_PATHS=("$@")
else
    SEARCH_PATHS=("/")
fi

# ----------------------------
# Validate Target Directory
# ----------------------------
if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Target directory '$TARGET_DIR' does not exist or is not a directory."
    exit 1
fi

# Resolve the absolute path of the target directory
TARGET_DIR=$(realpath "$TARGET_DIR")

echo "Target Directory: $TARGET_DIR"
echo "Search Paths: ${SEARCH_PATHS[*]}"
echo "----------------------------------------"

# ----------------------------
# Find all symlinks within the search paths
# ----------------------------
echo "Searching for symbolic links..."

# Using find to locate all symlinks in the specified search paths
# Redirecting errors to /dev/null to suppress permission denied messages
mapfile -t SYMLINKS < <(find "${SEARCH_PATHS[@]}" -type l 2>/dev/null)

echo "Total symlinks found: ${#SYMLINKS[@]}"
echo "----------------------------------------"

# ----------------------------
# Iterate through all subdirectories of TARGET_DIR
# ----------------------------
# Using find to list all immediate and nested subdirectories
mapfile -t SUBDIRS < <(find "$TARGET_DIR" -type d)

echo "Total subdirectories in target: ${#SUBDIRS[@]}"
echo "----------------------------------------"

# ----------------------------
# Create an associative array to map subdirectories to their symlinks
# ----------------------------
declare -A SYMLINK_MAP

# Iterate through all found symlinks
for symlink in "${SYMLINKS[@]}"; do
    # Resolve the absolute path the symlink points to
    TARGET=$(readlink -f "$symlink" 2>/dev/null)

    # Continue if readlink failed (e.g., broken symlink)
    if [ $? -ne 0 ] || [ -z "$TARGET" ]; then
        continue
    fi

    # Check if the target is within the TARGET_DIR
    if [[ "$TARGET" == "$TARGET_DIR"/* ]]; then
        # Identify which subdirectory it points to
        # Find the immediate subdirectory under TARGET_DIR
        SUBDIR="${TARGET#$TARGET_DIR/}"
        SUBDIR_FIRST="${SUBDIR%%/*}"  # Extract the first level subdirectory

        # Handle the case where the target is the TARGET_DIR itself
        if [ -z "$SUBDIR_FIRST" ]; then
            SUBDIR_FIRST="(target directory itself)"
        fi

        # Append the symlink to the corresponding subdirectory in the map
        SYMLINK_MAP["$SUBDIR_FIRST"]+="$symlink -> $TARGET"$'\n'
    fi
done

# ----------------------------
# Print the results
# ----------------------------
echo "Symbolic Links pointing to subdirectories of '$TARGET_DIR':"
echo "----------------------------------------"

for subdir in "${!SYMLINK_MAP[@]}"; do
    echo "Subdirectory: $subdir"
    echo "----------------------------------------"
    echo -e "${SYMLINK_MAP[$subdir]}"
    echo
done

# ----------------------------
# End of Script
# ----------------------------

