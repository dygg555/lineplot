import socket
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from collections import defaultdict
import threading
import sys

# ===== 用户配置区域 ===== 通道名称不能相同
LABELS = {
    "测试通道": ["dd0", "dd1", "dd2"],   # 通道0
    "正式通道": ["xx0", "xx1", "xx2"],   # 通道1
    # "xx通道": ["xx0", "xx1", "xx2"]   # 通道2
}

# 数据格式 "0,data0,data1,data2......" 通道0
#        "1,data0,data1,data2......" 通道1

UDP_IP = "0.0.0.0"  # 监听所有IP
UDP_PORT = 5005     # 端口号
MAX_POINTS = 500    # 每个曲线最大数据点数
COLORS = ['c', 'm', 'y', 'r', 'g', 'b']  # 曲线颜色(可循环使用)

# ===== 全局数据存储 =====
data = defaultdict(lambda: defaultdict(list))
lock = threading.Lock()  # 线程锁

# ===== UDP 接收线程 =====
class UdpListener(QtCore.QThread):
    def __init__(self):
        super().__init__()
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.5)  # 设置超时以便定期检查running状态

    def run(self):
        self.sock.bind((UDP_IP, UDP_PORT))
        print(f"Listening on UDP {UDP_IP}:{UDP_PORT}")

        while self.running:
            try:
                raw_data, _ = self.sock.recvfrom(1024)
                decoded = raw_data.decode().strip().split(',')
                channel = int(decoded[0])
                values = list(map(float, decoded[1:]))
                
                with lock:
                    # 检查通道是否在LABELS的范围内
                    if channel < len(LABELS):
                        channel_name = list(LABELS.keys())[channel]
                        max_curves = len(LABELS[channel_name])
                        for curve_idx in range(min(max_curves, len(values))):
                            data[channel][curve_idx].append(values[curve_idx])
                            if len(data[channel][curve_idx]) > MAX_POINTS:
                                data[channel][curve_idx].pop(0)
            except socket.timeout:
                continue  # 超时是正常的，用于检查running状态
            except Exception as e:
                print(f"Error parsing data: {e}")

    def stop(self):
        self.running = False
        self.wait()
        self.sock.close()  # 确保socket被关闭

# ===== 主窗口 =====
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UDP 实时曲线显示 (可配置)")
        self.resize(1600, 1200)
        
        # 主控件和布局
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QtWidgets.QVBoxLayout(self.central_widget)
        
        # 创建绘图区域
        self.create_plots()
        
        # 定时器更新曲线
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(30)  # ~33fps

    def create_plots(self):
        """根据LABELS配置创建绘图区域"""
        self.plots = []
        self.curves = {}
        
        # 遍历LABELS中的通道
        for channel_idx, (channel_name, curve_names) in enumerate(LABELS.items()):
            # 创建绘图部件
            plot = pg.PlotWidget(title=channel_name)  # 使用通道名称作为标题
            plot.setYRange(-1, 1)  # 初始Y轴范围
            plot.addLegend()
            self.main_layout.addWidget(plot)
            self.plots.append(plot)
            
            # 创建曲线对象
            self.curves[channel_idx] = []
            for curve_idx, curve_name in enumerate(curve_names):
                color = COLORS[curve_idx % len(COLORS)]
                curve = plot.plot([], [], name=str(curve_idx) + ":" + curve_name, pen=color)
                self.curves[channel_idx].append(curve)
    def update_plots(self):
        """更新所有曲线数据"""
        with lock:
            for channel_idx in range(len(LABELS)):
                y_min, y_max = float('inf'), -float('inf')
                curve_names = list(LABELS.values())[channel_idx]
                num_curves = len(curve_names)
                
                for curve_idx in range(num_curves):
                    y_data = data[channel_idx].get(curve_idx, [])
                    if y_data:
                        self.curves[channel_idx][curve_idx].setData(y_data)
                        y_min = min(y_min, min(y_data))
                        y_max = max(y_max, max(y_data))
                
                # 调整Y轴范围
                if y_min != float('inf') and y_max != -float('inf'):
                    self.plots[channel_idx].setYRange(y_min - 0.1, y_max + 0.1)

    def closeEvent(self, event):
        self.timer.stop()
        udp_thread.stop()
        event.accept()

# ===== 启动应用 =====
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    # 启动UDP线程
    udp_thread = UdpListener()
    udp_thread.start()
    
    # 创建主窗口
    win = MainWindow()
    win.show()
    
    # 运行应用
    ret = app.exec_()
    udp_thread.stop()
    sys.exit(ret)