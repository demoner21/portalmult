curl -X POST "http://127.0.0.1:8000/visualize/?rgb_image=True" \
-H "accept: application/json" \
-H "Content-Type: multipart/form-data" \
-F "files=@Sentinel_B4.tif" \
-F "files=@Sentinel_B3.tif" \
-F "files=@Sentinel_B2.tif" \
--output output_image.png