#!/bin/bash

# Set base URL for prediction endpoint
PREDICTION_URL="http://localhost:8000/predict/"

# Function to process images in a directory
process_directory() {
    local dir_path="$1"
    local output_file="$2"

    # Check if directory exists
    if [ ! -d "$dir_path" ]; then
        echo "Error: Directory $dir_path does not exist"
        return 1
    fi

    # Check if directory is empty
    if [ -z "$(ls -A "$dir_path")" ]; then
        echo "Warning: Directory $dir_path is empty"
        return 1
    fi

    echo "Processing directory: $dir_path"
    
    # Measure total processing time
    time curl -X POST "$PREDICTION_URL" \
        -F "files=@$dir_path/Sentinel_B1.tif" \
        -F "files=@$dir_path/Sentinel_B2.tif" \
        -F "files=@$dir_path/Sentinel_B3.tif" \
        -F "files=@$dir_path/Sentinel_B4.tif" \
        -F "files=@$dir_path/Sentinel_B5.tif" \
        -F "files=@$dir_path/Sentinel_B6.tif" \
        -F "files=@$dir_path/Sentinel_B7.tif" \
        -F "files=@$dir_path/Sentinel_B8.tif" \
        -F "files=@$dir_path/Sentinel_B8A.tif" \
        -F "files=@$dir_path/Sentinel_B9.tif" \
        -F "files=@$dir_path/Sentinel_B11.tif" \
        -F "files=@$dir_path/Sentinel_B12.tif" \
        -F "files=@$dir_path/NDVI.tif" \
        -F "files=@$dir_path/NDWI.tif" \
        -F "files=@$dir_path/SAVI.tif" \
        -F "files=@$dir_path/BSI.tif" | jq '.' > "$output_file"
}

# Main script execution
main() {
    # Directories with present and absent data
    PRESENT_DATA_DIR="./present_data"
    ABSENT_DATA_DIR="./absent_data"

    # Output files
    #PRESENT_OUTPUT="present_results.json"
    #ABSENT_OUTPUT="absent_results.json"

    # Process each directory
    process_directory "$PRESENT_DATA_DIR" "$PRESENT_OUTPUT"
    process_directory "$ABSENT_DATA_DIR" "$ABSENT_OUTPUT"

    # Compare results if both exist
    if [ -f "$PRESENT_OUTPUT" ] && [ -f "$ABSENT_OUTPUT" ]; then
        echo "Comparing results..."
        diff "$PRESENT_OUTPUT" "$ABSENT_OUTPUT"
    fi
}

# Run the main function
main