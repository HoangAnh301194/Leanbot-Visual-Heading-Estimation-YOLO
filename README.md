# Hướng dẫn sử dụng hệ thống Camera AI Leanbot Tracking và PID Control

## 1. Quy trình triển khai hệ thống
- Chạy file code [leanbotCameraController.py](LeanbotTinyRC_AI_PIDControl\leanbotCameraController.py)
- Cắm camera ( --source có thể là 0 hoặc 1)
- Khi hiển thị lên cửa sổ OpenCV, chỉnh lại cam để cho cân bằng lại sa bàn. 
- tải các requirement nếu chưa cài : [requirements.txt](requirements.txt)
## 2. Lệnh chạy đầy đủ

```bash
python leanbotCameraController.py \
  --show \
  --source 1 \
  --width 1280 \
  --height 720 \
  --fps 30.0 \
  --ble 343944 \
  --device CPU \
  --full-model "models\yolo11n_latest_version\best_fp16_no_nms_imgsz640_openvino_model" \
  --tracking-model "models\yolo11n_latest_version\best_fp16_no_nms_imgsz160_openvino_model" \
  --conf 0.25 \
  --roi_conf 0.15 \
  --topk 100 \
  --iou 0.5 \
  --mag-threshold 2.0 \
  --smooth-window 18 \
  --smooth-index 0 \
  --smooth-K 1.0 \
  --target-config "target_config.json" \
  --set-target-time 3.0 \
  --set-target-speed 1500 \
  --kp-angle 30.0 \
  --kd-angle 0.0 \
  --kp-angle2 0.01 \
  --kd-angle2 0.04 \
  --heading-tol 20.0 \
  --kp-angle3 20.0 \
  --kd-angle3 0.01 \
  --ki-angle3 0.0 \
  --heading-tol3 5.0 \
  --settle-time-ms 500.0 \
  --fwd-bwd-time 3.0 \
  --fwd-bwd-speed 2000 \
  --kp-spin 5.0 \
  --spin-speed 100 \
  --lost-dataset-dir "..\lost_tracking_dataset"
```

  ### Giải thích các tham số

  - **`--show`**: Mở các cửa sổ OpenCV trực quan, gồm cửa sổ nhận diện, ROI crop và đồ thị góc.
  - **`--source`**: ID cổng camera, có thể là `0` hoặc `1`.
  - **`--width`**, **`--height`**: Độ phân giải khung hình camera, mặc định là `1280 x 720`.
  - **`--fps`**: Giới hạn FPS tối đa của camera, mặc định là `30.0`.
  - **`--ble`**: ID kết nối Bluetooth BLE của Leanbot.
  - **`--device`**: Thiết bị chạy OpenVINO, gồm `CPU`, `GPU` hoặc `AUTO`.
  - **`--full-model`**: Đường dẫn đến thư mục mô hình OpenVINO Full `640 x 640`.
  - **`--tracking-model`**: Đường dẫn đến thư mục mô hình OpenVINO ROI `160 x 160`.
  - **`--conf`**: Ngưỡng confidence cho mô hình Full `640`, mặc định là `0.25`.
  - **`--roi_conf`**: Ngưỡng confidence cho mô hình ROI `160`, mặc định là `0.15`.
  - **`--topk`**: Số lượng anchor có confidence cao nhất được giữ lại, mặc định là `100`.
  - **`--iou`**: Ngưỡng IoU dùng để nhóm các anchor chồng lấn, mặc định là `0.5`.
  - **`--mag-threshold`**: Ngưỡng độ lớn vector tối thiểu để chấp nhận một nhóm anchor, mặc định là `2.0`.
  - **`--smooth-window`**: Kích thước cửa sổ trượt dùng để làm mịn góc, mặc định là `18`.
  - **`--smooth-index`**: Chỉ số đánh giá tangent trễ trong bộ làm mịn, mặc định là `0`.
  - **`--smooth-K`**: Hằng số trọng số khi hợp nhất góc, mặc định là `1.0`.
  - **`--target-config`**: Đường dẫn file JSON lưu và nạp tọa độ, góc đích, mặc định là `target_config.json`.
  - **`--set-target-time`**: Thời gian chạy mỗi chiều khi hiệu chuẩn target bằng phím `T`, mặc định là `3.0` giây.
  - **`--set-target-speed`**: Vận tốc bánh xe khi hiệu chuẩn target bằng phím `T`, mặc định là `1500`.
  - **`--kp-angle`**, **`--kd-angle`**: Hệ số PID Phase 1 để xoay Leanbot về hướng target pixel, mặc định lần lượt là `30.0` và `0.0`.
  - **`--kp-angle2`**, **`--kd-angle2`**: Hệ số PID Phase 2 để di chuyển bám target pixel, mặc định lần lượt là `0.01` và `0.04`.
  - **`--heading-tol`**: Dung sai góc để chuyển từ Phase 1 sang Phase 2, mặc định là `20.0` độ.
  - **`--target-heading`**: Góc heading mục tiêu cho Phase 3.
  - **`--kp-angle3`**, **`--kd-angle3`**, **`--ki-angle3`**: Hệ số PID Phase 3 để tinh chỉnh góc heading cuối cùng, mặc định lần lượt là `20.0`, `0.01` và `0.0`.
  - **`--heading-tol3`**: Dung sai góc kết thúc của Phase 3, mặc định là `5.0` độ.
  - **`--settle-time-ms`**: Thời gian Leanbot phải ổn định tại góc mục tiêu, mặc định là `500.0` ms.
  - **`--fwd-bwd-time`**: Thời gian chạy mỗi chiều trong phép thử tiến/lùi Phase 4, mặc định là `3.0` giây. Đặt `0` để tắt.
  - **`--fwd-bwd-speed`**: Vận tốc bánh xe trong phép thử tiến/lùi Phase 4, mặc định là `2000`.
  - **`--kp-spin`**: Hệ số quy đổi sai số góc thành số bước xoay sau Phase 4, mặc định là `5.0` bước/độ.
  - **`--spin-speed`**: Vận tốc khi thực hiện lệnh `spinSteps()` sau Phase 4, mặc định là `100`.
  - **`--lost-dataset-dir`**: Thư mục lưu dataset khi Leanbot bị mất tracking. Nếu bỏ trống, mặc định là thư mục `lost_tracking_dataset` ở ngoài thư mục dự án.


`Lệnh chạy nhanh với các param mặc định ( đã lựa chọn tối ưu tương đối)

```bash
python leanbotCameraController.py \
  --show \
  --source 1 \
  --ble 654321
```

## 3. Cách sử dụng : 
- **Set target heading angle và target pixel** :
    - Đặt Leanbot tại vị trí đích target mong muốn 
    - Xuay leanbot theo góc target angle mong muốn
    - Bấm phím "t" để tiến hành lưu vị gí target pixel 
    - Leanbot sẽ tự động đi tiến lùi ( run_fw_bw()) để vẽ ra đường trajectory heading và tính toán ra góc target angle 
- **Chạy điều khiển PID tự động về vị trí target pixe và xuay tới góc target angle**
    - Đặt Leanbot tại các vị trí ngẫu nhiên muốn khảo sát 
    - bấm phím "s" để bắt đầu quá trình điều khiển Leanbot tự động 
    - Khi tới đích Leanbot tự động xuay góc về phía target angle 
    - Toàn bộ các phase chuyển động như sau : 
        - Phase 1 : PID xuay Leanbot về hướng target pixel 
        - Phase 2 : PID di chuyển liên tục về target pixel 
        - Phase 3 : PID xuay Leanbot về hướng góc target angle 
        - Phase 4 : Leanbot tự động đi tiến lùi (run_fw_bw) để tính ra góc heading và so sánh với target heading angle --> angle error 
        - Phase 5 : từ angle error tính toán ra số bước để xuay Leanbot bằng spinSteps() với công thức ước lượng : rotationStep = Kp*error ( Kp và speep sẽ được config bằng argument khi thực nghiệm ) 
        - Phase 6 : Lặp lại nhưu phase 4 , tính toán ra sai số góc và đánh giá lại bằng print log terminal

