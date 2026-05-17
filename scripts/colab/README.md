# Triển khai bộ phân loại ý định trên Google Colab

Bộ phân loại ý định của HanoiAir dùng mô hình Qwen3-4B đã được tinh chỉnh, cần GPU để chạy. Vì không phải máy nào cũng có GPU, hệ thống triển khai bộ phân loại này trên Google Colab với GPU T4 miễn phí, rồi mở một địa chỉ web công khai để các thành phần chạy trên máy của bạn có thể kết nối tới.


## Các bước thực hiện

Trước tiên, mở tệp `ollama_router_colab.ipynb` trên Google Colab tại địa chỉ `https://colab.research.google.com`. Vào mục Runtime, chọn Change runtime type, chọn GPU T4 rồi lưu lại. Chạy tuần tự các cell từ một tới bảy. Lần chạy đầu tiên mất khoảng ba tới năm phút để cài đặt Ollama, tải mô hình và mở tunnel.

Sau khi cell sáu chạy xong, notebook sẽ in ra một địa chỉ web công khai dạng như sau.

```
PUBLIC URL: https://xxxxxxxx-xxxxxxxx.trycloudflare.com
```

Mở tệp `.env` ở thư mục gốc của dự án, điền địa chỉ này vào trường `OLLAMA_BASE_URL`, đặt `USE_SLM_ROUTER` bằng `true`. Khởi động lại các dịch vụ Docker để áp dụng cấu hình mới.

```bash
docker compose restart api
```

Kiểm tra kết nối thành công bằng lệnh sau, trường `router` phải có giá trị `ok`.

```bash
curl http://localhost:8000/ready
```


## Một số lưu ý khi dùng Colab miễn phí

Google Colab phiên bản miễn phí có thời lượng phiên giới hạn, runtime sẽ tự đóng sau khoảng chín mươi phút không tương tác, và tối đa khoảng mười hai giờ liên tục. Khi runtime đóng, địa chỉ web tunnel cũng mất hiệu lực, bạn cần chạy lại notebook và cập nhật địa chỉ mới vào tệp `.env`. Độ trễ kết nối từ máy của bạn qua Cloudflare tới Colab thường nằm trong khoảng năm trăm tới một nghìn năm trăm mili giây, đủ nhanh cho mục đích trình diễn nhưng chậm hơn so với chạy mô hình trực tiếp trên máy có GPU.


## Khắc phục sự cố

Nếu cell đầu tiên báo không tìm thấy GPU, vào lại mục Runtime, chọn Change runtime type, chọn GPU T4 rồi nhấn Save và Restart runtime.

Nếu cell kiểm thử báo lỗi quá thời gian chờ trong lần gọi đầu tiên, đó là do mô hình đang được tải lên bộ nhớ GPU, thường mất từ ba mươi tới chín mươi giây. Chạy lại cell đó là được.

Nếu lệnh kiểm tra trên máy báo `router` ở trạng thái `disabled`, kiểm tra lại xem các biến môi trường đã được truyền vào container chưa bằng lệnh sau.

```bash
docker compose exec api env | grep OLLAMA
```

Đầu ra phải hiện đủ ba biến `OLLAMA_BASE_URL`, `OLLAMA_MODEL` và `USE_SLM_ROUTER`. Nếu thiếu, kiểm tra lại tệp `.env` và khởi động lại các dịch vụ Docker.
