import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QListWidget, QProgressBar,
                             QSpinBox, QCheckBox, QGroupBox, QFileDialog, 
                             QMessageBox, QWidget, QSplitter, QTextEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import rawpy
import imageio

class ConversionThread(QThread):
    """Поток для конвертации файлов"""
    progress = pyqtSignal(int)
    log_message = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)
    
    def __init__(self, file_list, output_dir, quality, delete_original=False):
        super().__init__()
        self.file_list = file_list
        self.output_dir = output_dir
        self.quality = quality
        self.delete_original = delete_original
        self.is_running = True
        
    def run(self):
        try:
            total_files = len(self.file_list)
            successful = 0
            
            for i, file_path in enumerate(self.file_list):
                if not self.is_running:
                    break
                    
                try:
                    self.log_message.emit(f"Конвертация: {os.path.basename(file_path)}")
                    
                    # Конвертация ORF в JPG
                    with rawpy.imread(file_path) as raw:
                        rgb = raw.postprocess()
                    
                    # Создаем имя выходного файла
                    output_filename = Path(file_path).stem + '.jpg'
                    output_path = os.path.join(self.output_dir, output_filename)
                    
                    # Сохраняем JPG
                    imageio.imsave(output_path, rgb, quality=self.quality)
                    successful += 1
                    
                    # Удаляем оригинал если нужно
                    if self.delete_original:
                        os.remove(file_path)
                        self.log_message.emit(f"Удален оригинал: {os.path.basename(file_path)}")
                    
                    self.log_message.emit(f"✅ Успешно: {output_filename}")
                    
                except Exception as e:
                    self.log_message.emit(f"❌ Ошибка {os.path.basename(file_path)}: {str(e)}")
                
                # Обновляем прогресс
                progress = int((i + 1) / total_files * 100)
                self.progress.emit(progress)
            
            self.finished_signal.emit(True)
            self.log_message.emit(f"Конвертация завершена! Успешно: {successful}/{total_files}")
            
        except Exception as e:
            self.log_message.emit(f"Критическая ошибка: {str(e)}")
            self.finished_signal.emit(False)
    
    def stop(self):
        self.is_running = False

class ORFConverterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.file_list = []
        self.conversion_thread = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("ORF to JPG Converter")
        self.setGeometry(100, 100, 900, 700)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Сплиттер для разделения интерфейса
        splitter = QSplitter(Qt.Vertical)
        
        # Верхняя панель - управление
        top_widget = QWidget()
        top_layout = QVBoxLayout()
        top_widget.setLayout(top_layout)
        
        # Панель выбора файлов
        file_selection_layout = QHBoxLayout()
        self.btn_add_files = QPushButton("Добавить файлы")
        self.btn_add_files.clicked.connect(self.add_files)
        self.btn_add_folder = QPushButton("Добавить папку")
        self.btn_add_folder.clicked.connect(self.add_folder)
        self.btn_clear_list = QPushButton("Очистить список")
        self.btn_clear_list.clicked.connect(self.clear_list)
        
        file_selection_layout.addWidget(self.btn_add_files)
        file_selection_layout.addWidget(self.btn_add_folder)
        file_selection_layout.addWidget(self.btn_clear_list)
        file_selection_layout.addStretch()
        
        # Список файлов
        self.file_list_widget = QListWidget()
        
        # Настройки конвертации
        settings_group = QGroupBox("Настройки конвертации")
        settings_layout = QHBoxLayout()
        
        # Качество
        quality_layout = QVBoxLayout()
        quality_layout.addWidget(QLabel("Качество JPG:"))
        self.quality_spinbox = QSpinBox()
        self.quality_spinbox.setRange(1, 100)
        self.quality_spinbox.setValue(95)
        self.quality_spinbox.setSuffix("%")
        quality_layout.addWidget(self.quality_spinbox)
        
        # Папка назначения
        output_layout = QVBoxLayout()
        output_layout.addWidget(QLabel("Папка для сохранения:"))
        self.output_label = QLabel("Использовать исходные папки")
        self.output_label.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        self.btn_choose_output = QPushButton("Выбрать папку")
        self.btn_choose_output.clicked.connect(self.choose_output_folder)
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.btn_choose_output)
        
        # Дополнительные опции
        options_layout = QVBoxLayout()
        self.delete_original_checkbox = QCheckBox("Удалить оригинальные ORF файлы после конвертации")
        options_layout.addWidget(self.delete_original_checkbox)
        
        settings_layout.addLayout(quality_layout)
        settings_layout.addLayout(output_layout)
        settings_layout.addLayout(options_layout)
        settings_layout.addStretch()
        settings_group.setLayout(settings_layout)
        
        # Кнопки управления
        control_layout = QHBoxLayout()
        self.btn_start = QPushButton("Начать конвертацию")
        self.btn_start.clicked.connect(self.start_conversion)
        self.btn_stop = QPushButton("Остановить")
        self.btn_stop.clicked.connect(self.stop_conversion)
        self.btn_stop.setEnabled(False)
        
        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.btn_stop)
        control_layout.addStretch()
        
        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        # Собираем верхнюю панель
        top_layout.addLayout(file_selection_layout)
        top_layout.addWidget(self.file_list_widget)
        top_layout.addWidget(settings_group)
        top_layout.addLayout(control_layout)
        top_layout.addWidget(self.progress_bar)
        
        # Нижняя панель - лог
        log_group = QGroupBox("Лог выполнения")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        
        # Добавляем в сплиттер
        splitter.addWidget(top_widget)
        splitter.addWidget(log_group)
        splitter.setSizes([500, 200])
        
        main_layout.addWidget(splitter)
        
        # Статус бар
        self.status_label = QLabel("Готов к работе")
        self.statusBar().addWidget(self.status_label)
        
        self.output_folder = None
        
    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Выберите ORF файлы", "", "ORF Files (*.orf *.ORF)"
        )
        if files:
            self.file_list.extend(files)
            self.update_file_list()
            self.log_text.append(f"Добавлено файлов: {len(files)}")
            
    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с ORF файлами")
        if folder:
            orf_files = []
            for ext in ['*.orf', '*.ORF']:
                orf_files.extend(Path(folder).rglob(ext))
            
            if orf_files:
                self.file_list.extend([str(f) for f in orf_files])
                self.update_file_list()
                self.log_text.append(f"Добавлено файлов из папки: {len(orf_files)}")
            else:
                QMessageBox.information(self, "Информация", "ORF файлы не найдены в выбранной папке")
                
    def choose_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения JPG")
        if folder:
            self.output_folder = folder
            self.output_label.setText(folder)
            
    def clear_list(self):
        self.file_list.clear()
        self.file_list_widget.clear()
        self.log_text.append("Список файлов очищен")
        
    def update_file_list(self):
        self.file_list_widget.clear()
        for file_path in self.file_list:
            self.file_list_widget.addItem(os.path.basename(file_path))
            
    def start_conversion(self):
        if not self.file_list:
            QMessageBox.warning(self, "Предупреждение", "Добавьте файлы для конвертации")
            return
            
        # Определяем папку для сохранения
        if self.output_folder:
            output_dir = self.output_folder
            os.makedirs(output_dir, exist_ok=True)
        else:
            # Используем папки исходных файлов
            output_dir = None
            
        # Запускаем конвертацию в отдельном потоке
        self.conversion_thread = ConversionThread(
            self.file_list,
            output_dir if output_dir else os.path.dirname(self.file_list[0]),
            self.quality_spinbox.value(),
            self.delete_original_checkbox.isChecked()
        )
        
        self.conversion_thread.progress.connect(self.update_progress)
        self.conversion_thread.log_message.connect(self.add_log_message)
        self.conversion_thread.finished_signal.connect(self.conversion_finished)
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.conversion_thread.start()
        self.log_text.append("=== Начало конвертации ===")
        
    def stop_conversion(self):
        if self.conversion_thread and self.conversion_thread.isRunning():
            self.conversion_thread.stop()
            self.conversion_thread.wait()
            self.log_text.append("Конвертация остановлена пользователем")
            
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        
    def add_log_message(self, message):
        self.log_text.append(message)
        # Автопрокрутка к последнему сообщению
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
        
    def conversion_finished(self, success):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        if success:
            self.status_label.setText("Конвертация завершена успешно")
        else:
            self.status_label.setText("Конвертация завершена с ошибками")

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Современный стиль
    
    converter = ORFConverterApp()
    converter.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()