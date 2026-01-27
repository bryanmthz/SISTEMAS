def get_stylesheet(dark_mode):
    if dark_mode:
        return """
        QWidget { 
            background-color: #2D2D2D;
            color: #FFFFFF;
            font-family: 'Segoe UI', sans-serif;
        }
        QGroupBox {
            border: 1px solid #444;
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 15px;
            font-weight: bold;
            color: #FFFFFF;
        }
        QDoubleSpinBox {
            padding: 5px;
            border: 1px solid #444;
            border-radius: 4px;
            background-color: #3A3A3A;
            color: #FFFFFF;
        }
        QTextEdit {
            background: #3A3A3A;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
            font-family: monospace;
            color: #FFFFFF;
        }
        QPushButton {
            background-color: #3B82F6;
            color: white;
            padding: 10px 20px;
            border-radius: 6px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2563EB;
        }
        QCheckBox {
            color: #FFFFFF;
        }
        """
    else:
        return """
        QWidget { 
            background-color: #FAF9F6;
            color: #000000;
            font-family: 'Segoe UI', sans-serif;
        }
        QGroupBox {
            border: 1px solid #D1D5DB;
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 15px;
            font-weight: bold;
            color: #374151;
        }
        QDoubleSpinBox {
            padding: 5px;
            border: 1px solid #D1D5DB;
            border-radius: 4px;
            background-color: #FFFFFF;
            color: #000000;
        }
        QTextEdit {
            background: #FFFFFF;
            border: 1px solid #D1D5DB;
            border-radius: 6px;
            padding: 10px;
            font-family: monospace;
            color: #000000;
        }
        QPushButton {
            background-color: #3B82F6;
            color: white;
            padding: 10px 20px;
            border-radius: 6px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2563EB;
        }
        QCheckBox {
            color: #000000;
        }
        """
