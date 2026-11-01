# 🏸 Badminton Hawk-Eye Pro (Android & Computer Vision Engine)

Hệ thống phân tích video cầu lông tự động, hiển thị đồ họa lớp phủ tương tác (AR HUD Overlay) và tái hiện đường bay 2D/3D thu nhỏ như hệ thống **Hawk-Eye chuyên nghiệp tại các giải đấu BWF**.

---

## 📑 Mục lục
1. [Kiến trúc Tổng thể](#-kiến-trúc-tổng-thể)
2. [Chi tiết Thuật toán Computer Vision](#-chi-tiết-thuật-toán-computer-vision)
   - [Tự động nhận diện sân & Ma trận Homography](#1-tự-động-nhận-diện-sân--homography)
   - [Thuật toán ngoại suy góc sân bị khuất / ngoài khung hình](#2-thuật-toán-ngoại-suy-góc-sân-occlusion)
   - [Tracking người chơi & Đo quãng đường di chuyển](#3-tracking-người-chơi--quãng-đường-di-chuyển)
   - [Tracking cầu, khử Motion Blur & Đo tốc độ](#4-tracking-cầu--đo-tốc-độ-kmh)
   - [Trọng tài ảo & Thống kê pha cầu (In/Out)](#5-trọng-tài-ảo--thống-kê-pha-cầu)
3. [Tối ưu hóa Hệ điều hành & Khắc phục lỗi Xiaomi (MIUI / HyperOS)](#-tối-ưu-hóa-hệ-điều-hành-xiaomi-miui--hyperos)
4. [Cấu trúc Mã nguồn Dự án](#-cấu-trúc-mã-nguồn-dự-án)
5. [Hướng dẫn Build ra file APK cài đặt](#-hướng-dẫn-build-ra-file-apk-cài-đặt)
   - [Cách 1: Tự động 100% bằng GitHub Actions (Khuyên dùng)](#cách-1-build-tự-động-bằng-github-actions-không-cần-cài-đặt-gì)
   - [Cách 2: Build trực tiếp trên máy bằng Script build_apk.sh](#cách-2-build-bằng-script-build_apksh)
   - [Cách 3: Chạy Engine Python Backend & Xử lý Batch](#cách-3-chạy-engine-python-backend--cli)

---

## 🏛 Kiến trúc Tổng thể

Dự án áp dụng mô hình **Dual-Engine Architecture** linh hoạt:
- **Mobile Client (Flutter & Native Kotlin):**
  - Giao diện người dùng thời gian thực 60Hz/120Hz mượt mà.
  - Bộ điều khiển video và thanh trượt có bộ đệm **Throttler/Debouncer** loại bỏ 100% độ trễ UI.
  - Native MethodChannel tích hợp Android Photo Picker (`ActivityResultContracts.PickVisualMedia`) và Storage Access Framework (SAF) bảo mật.
  - Engine toán học nội suy Pure Dart: Giải ma trận Homography DLT (Gaussian Elimination) và bộ lọc Kalman 4 chiều $(\mathbf{x} = [x, y, v_x, v_y]^T)$ chạy offline trực tiếp on-device.
- **Computer Vision Engine (Python Backend & CLI):**
  - Xử lý sâu theo từng khung hình với OpenCV, NumPy, SciPy và FastAPI.
  - Phân tích và kết xuất video kèm lớp phủ đồ họa chuẩn truyền hình thể thao.

---

## 🔬 Chi tiết Thuật toán Computer Vision

### 1. Tự động nhận diện sân & Homography
- **Phân đoạn mặt thảm sân:** Sử dụng không gian màu HSV ($H \in [30, 90], S \in [25, 255], V \in [25, 255]$) kết hợp phép biến đổi hình thái học (Morphological Open & Close) để trích xuất thảm sân cầu lông chuẩn.
- **Nhận diện vạch sơn trắng:** Áp dụng bộ lọc ngưỡng sáng cao ($V \ge 165$) giới hạn bên trong vùng mặt sân.
- **Biến đổi Hough Lines:** Phát hiện các đường biên dọc (sidelines) và đường biên ngang (baselines).
- **Ánh xạ tọa độ thế giới chuẩn BWF (Meters):**
  - Đánh đơn (Singles): $13.40\text{ m} \times 5.18\text{ m}$
  - Đánh đôi (Doubles): $13.40\text{ m} \times 6.10\text{ m}$
  - Lưới tại vị trí $Y = 6.70\text{ m}$, vạch giao cầu ngắn tại $Y = 4.72\text{ m}$ và $Y = 8.68\text{ m}$.
- **Ma trận biến đổi phối cảnh (Homography Matrix $H$):**
  $$\begin{bmatrix} x_w \\ y_w \\ 1 \end{bmatrix} \sim H \begin{bmatrix} u \\ v \\ 1 \end{bmatrix} = \begin{bmatrix} h_{11} & h_{12} & h_{13} \\ h_{21} & h_{22} & h_{23} \\ h_{31} & h_{32} & h_{33} \end{bmatrix} \begin{bmatrix} u \\ v \\ 1 \end{bmatrix}$$
  Giải bằng thuật toán RANSAC kết hợp Direct Linear Transformation (DLT).

### 2. Thuật toán ngoại suy góc sân (Occlusion / Missing Corner)
Khi góc sân bị cầu thủ che khuất hoặc vượt ra ngoài khung hình (như ở góc dưới của các video quay dọc TikTok/Reels):
1. Tính phương trình 2 đường thẳng biên dọc bên trái $L_1: A_1 x + B_1 y + C_1 = 0$ và bên phải $L_2: A_2 x + B_2 y + C_2 = 0$.
2. Tìm điểm tụ (Vanishing Point) của phối cảnh: $V_y = L_1 \cap L_2$.
3. Sử dụng tỷ số kép xạ ảnh (Projective Cross-Ratio) từ các vạch giao cầu đã biết để khôi phục chính xác tọa độ góc bị thiếu mà không làm méo mó ma trận $H$.

### 3. Tracking người chơi & Quãng đường di chuyển
- Phân đoạn tiền cảnh bằng thuật toán **MOG2 Background Subtractor** có khử bóng.
- Lọc theo nửa sân: Phía trên lưới (Momota - Top Player) và phía dưới lưới (Axelsen - Bottom Player).
- Trích xuất điểm tiếp đất của bàn chân: $P_{\text{foot}} = (x_{\text{center}}, y_{\text{bottom}})$.
- Chiếu điểm chân qua ma trận $H$ xuống hệ tọa độ BWF thực:
  $$(X_m, Y_m) = H \cdot P_{\text{foot}}$$
- Đo tổng quãng đường thực tế di chuyển (mét):
  $$D_{\text{total}} = \sum_{k=1}^{N} \sqrt{(X_{k} - X_{k-1})^2 + (Y_{k} - Y_{k-1})^2}$$

### 4. Tracking cầu & Đo tốc độ (km/h)
- **Cơ chế độ nhạy cao (High Sensitivity Mode):**
  - Trừ nền 3 khung hình liên tiếp để phát hiện chuyển động tốc độ cao:
    $$D_t = |I_t - I_{t-1}| \odot |I_{t+1} - I_t|$$
  - Kết hợp mặt nạ độ sáng trắng để lọc quả cầu nhỏ ($3 \le \text{Area} \le 180\text{ px}$).
- **Bộ lọc Kalman 4 chiều:**
  - Dự đoán vị trí khi cầu bị mờ do chuyển động (Motion Blur) hoặc bị vợt/người che khuất.
- **Tính toán tốc độ thực tế (km/h):**
  $$v_{\text{km/h}} = \left( \frac{\sqrt{\Delta X^2 + \Delta Y^2}}{\Delta t} \right) \times 3.6 \quad \text{với } \Delta t = \frac{1}{\text{FPS}}$$

### 5. Trọng tài ảo & Thống kê pha cầu
- **Tự động đếm Shot:** Phát hiện thời điểm đổi hướng vận tốc ($\Delta v_y$ đổi dấu hoặc gia tốc đổi chiều đột ngột tại vị trí người chơi).
- **Phán quyết In / Out:** Khi tốc độ cầu giảm dưới $12\text{ km/h}$ gần mặt sàn, kiểm tra tọa độ thế giới:
  $$-0.05 \le X_m \le W_{\text{bwf}} + 0.05 \quad \text{và} \quad -0.05 \le Y_m \le L_{\text{bwf}} + 0.05$$
  Nếu nằm ngoài biên $\rightarrow$ Phán quyết **"OUT"**; nếu nằm trong biên $\rightarrow$ Phán quyết **"IN"**.

---

## 📱 Tối ưu hóa Hệ điều hành (Xiaomi, MIUI & HyperOS)

Xiaomi MIUI và HyperOS nổi tiếng với chính sách bảo mật Scoped Storage nghiêm ngặt và trình dọn dẹp bộ nhớ/tối ưu pin ngầm thường xuyên gây crash ứng dụng chọn file. Dự án đã xử lý triệt để:

1. **Không dùng `ACTION_GET_CONTENT` generic:** Thay vào đó sử dụng `ActivityResultContracts.PickVisualMedia` (hỗ trợ từ Android 4.4 đến Android 14+ qua Google Play Services) kết hợp dự phòng Storage Access Framework (`ACTION_OPEN_DOCUMENT`).
2. **Khắc phục lỗi Scoped Storage & Permission Denial:**
   - Khi người dùng chọn video từ ứng dụng hệ thống, Android trả về một `content://` URI có thời hạn cấp quyền ngắn. Nếu truyền trực tiếp URI này sang luồng nền hoặc C++ engine sẽ gây lỗi `SecurityException: Permission Denial` hoặc `FileUriExposedException`.
   - **Giải pháp trong `MainActivity.kt`:** Ứng dụng mở trực tiếp luồng `contentResolver.openInputStream(uri)`, đọc theo từng buffer 64KB và ghi bản sao an toàn vào thư mục riêng của app: `context.cacheDir/cached_video.mp4`. File này nằm trong sandbox của ứng dụng nên có thể truy cập bằng đường dẫn POSIX cục bộ với tốc độ đọc cực đại và không bao giờ bị lỗi quyền.
3. **Phân quyền theo cấp độ SDK:**
   - Android 13+ (API 33+): Khai báo và yêu cầu `android.permission.READ_MEDIA_VIDEO`.
   - Android 10-12 (API 29-32): Sử dụng `READ_EXTERNAL_STORAGE` với `android:maxSdkVersion="32"`.
   - Android 10: Kích hoạt `android:requestLegacyExternalStorage="true"`.
4. **Tối ưu hóa UI Thread (60Hz / 120Hz):**
   - Bộ điều khiển `Throttler` giới hạn tần suất seek video tối đa 30-60 sự kiện/giây, ngăn chặn nghẽn bộ giải mã MediaCodec khi kéo thanh trượt liên tục trên màn hình 120Hz.

---

## 📁 Cấu trúc Mã nguồn Dự án

```
badminton_hawkeye/
├── .github/
│   └── workflows/
│       └── build_apk.yml             # CI/CD tự động build APK trên GitHub
├── android/
│   ├── app/
│   │   ├── src/main/
│   │   │   ├── AndroidManifest.xml   # Khai báo quyền tương thích Xiaomi/HyperOS
│   │   │   ├── kotlin/com/hawkeye/badminton/
│   │   │   │   └── MainActivity.kt  # SAF / PhotoPicker & Cache Copier an toàn
│   │   │   └── res/values/styles.xml
│   │   └── build.gradle              # Cấu hình Gradle & SDK 34
│   ├── build.gradle
│   └── settings.gradle
├── backend/                          # Computer Vision Engine (Python & OpenCV)
│   ├── court_detector.py             # Nhận diện sân, ngoại suy góc & Homography
│   ├── player_tracker.py             # Tracking 2 người chơi & tính quãng đường mét
│   ├── shuttlecock_tracker.py        # 3-frame diff, Kalman Filter & tính km/h
│   ├── virtual_referee.py            # Đếm cú đánh, máy trạng thái & phán quyết In/Out
│   ├── video_renderer.py             # Vẽ lớp phủ HUD, vệt sáng cầu & mini court 2D
│   ├── cli_analyze.py                # Xử lý video độc lập từ dòng lệnh
│   ├── server.py                     # Backend FastAPI & WebSocket streaming
│   └── requirements.txt
├── lib/                              # Mã nguồn Flutter (Clean Architecture)
│   ├── main.dart                     # Điểm khởi chạy ứng dụng
│   ├── core/
│   │   ├── constants/
│   │   │   └── bwf_dimensions.dart   # Thông số kích thước sân chuẩn BWF
│   │   ├── math/
│   │   │   ├── homography_matrix.dart# Bộ giải ma trận DLT & hình học xạ ảnh
│   │   │   └── kalman_filter.dart    # Bộ lọc Kalman 4 chiều cho cầu lông
│   │   ├── theme/
│   │   │   └── app_theme.dart        # Giao diện thể thao Hawk-Eye neon
│   │   └── utils/
│   │       └── debouncer.dart        # Throttler & Debouncer cho màn hình 120Hz
│   └── features/analyzer/
│       ├── domain/models/            # Court, Player, Shuttlecock, RallyStats
│       ├── data/services/
│       │   ├── xiaomi_safe_file_picker.dart
│       │   └── video_engine_service.dart
│       └── presentation/
│           ├── screens/hawkeye_screen.dart
│           └── widgets/
│               ├── hawkeye_painter.dart
│               ├── mini_court_widget.dart
│               ├── stats_hud_widget.dart
│               └── control_panel_widget.dart
├── build_apk.sh                      # Script tự động compile APK
├── run_server.sh                     # Script khởi chạy CV backend server
├── pubspec.yaml                      # Cấu hình thư viện Flutter
└── README.md
```

---

## 🚀 Hướng dẫn Build ra file APK Cài đặt

### Cách 1: Build tự động bằng GitHub Actions (Không cần cài đặt gì)
Đây là cách đơn giản và nhanh nhất:
1. Tạo một repository mới trên GitHub (Private hoặc Public).
2. Tải toàn bộ mã nguồn trong file ZIP này lên repository của bạn.
3. Vào tab **Actions** trên GitHub $\rightarrow$ Chọn workflow **"Build Badminton Hawk-Eye Android APK"** $\rightarrow$ Bấm **Run workflow**.
4. GitHub sẽ tự động khởi tạo máy ảo Ubuntu, cài đặt Java 17, Flutter SDK, biên dịch file APK Release trong khoảng 3 phút.
5. Sau khi hoàn thành, tải trực tiếp file `BadmintonHawkEye-Release-APK.zip` (chứa `app-release.apk`) về điện thoại và cài đặt!

### Cách 2: Build bằng Script `build_apk.sh`
Nếu máy tính của bạn đã có Flutter SDK và Android SDK:
```bash
# Cấp quyền thực thi
chmod +x build_apk.sh

# Chạy script build
./build_apk.sh
```
File APK cài đặt sẽ được lưu tại thư mục `build_output/app-release.apk`.

### Cách 3: Chạy Engine Python Backend & CLI
Để phân tích video hoặc chạy server độc lập:
```bash
cd backend
pip install -r requirements.txt

# Phân tích video trực tiếp qua CLI:
python3 cli_analyze.py \
  --input /duong_dan/video_cau_long.mp4 \
  --output video_da_phan_tich.mp4 \
  --mode singles \
  --player1 Momota \
  --player2 Axelsen

# Khởi chạy server FastAPI:
uvicorn server:app --host 0.0.0.0 --port 8000
```
