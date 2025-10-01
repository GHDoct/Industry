import sys
import systeme
import gui
from functools import partial
from PyQt5.QtWidgets import QApplication, QStackedWidget, QPushButton,\
                            QSpinBox, QGroupBox, QLabel, QGridLayout, QFileDialog
from PyQt5 import QtCore
from PyQt5.uic import loadUi

class MainWindow(QStackedWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi("uis/main.ui", self)
        self.ressources = [1]
        self.current_cell = 0
        self.current_cell_2 = 0
        self.familles = 1
        self.current_famille = 0
        self._reset_cell_infos()

        self.connect_buttons()
        self.connect_spinners()
    
    def connect_buttons(self):
        self.findChild(QPushButton, "cellule_prec").clicked.connect(self._cellule_prec_clic)
        self.findChild(QPushButton, "cellule_svt").clicked.connect(self._cellule_svt_clic)
        self.findChild(QPushButton, "preview_btn").clicked.connect(self._preview_clic)
        self.findChild(QPushButton, "preview_btn_2").clicked.connect(self._preview_clic)
        self.findChild(QPushButton, "btn_suivant").clicked.connect(self._svt_click)
        self.findChild(QPushButton, "btn_prec").clicked.connect(self._prec_click)
        self.findChild(QPushButton, "btn_prec_2").clicked.connect(self._prec_click)
        self.findChild(QPushButton, "cellule_prec_2").clicked.connect(self._prec_second_cell_click)
        self.findChild(QPushButton, "cellule_svt_2").clicked.connect(self._svt_second_cell_click)
        self.findChild(QPushButton, "fam_prec").clicked.connect(self._prec_fam_click)
        self.findChild(QPushButton, "fam_svt").clicked.connect(self._svt_fam_click)
        self.findChild(QPushButton, "btn_create_config").clicked.connect(self._create_config)
        self.findChild(QPushButton, "btn_load_config").clicked.connect(self._load_config)

    def connect_spinners(self):
        self.findChild(QSpinBox, "nb_cells").valueChanged.connect(self._change_nbCells)
        self.findChild(QSpinBox, "nb_ress_spin").valueChanged.connect(self._change_nbRess)
        self.findChild(QSpinBox, "nb_fam").valueChanged.connect(self._change_nbFam)

    def _cellule_prec_clic(self):
        self.current_cell -= 1
        self.findChild(QSpinBox, "nb_ress_spin").setValue(self.ressources[self.current_cell])
        self._change_nbCells()

    def _cellule_svt_clic(self):
        self.current_cell += 1
        self.findChild(QSpinBox, "nb_ress_spin").setValue(self.ressources[self.current_cell])
        self._change_nbCells()

    def _change_nbCells(self):
        val = self.findChild(QSpinBox, "nb_cells").value()
        if self.current_cell >= val:
            self.current_cell = val-1

        if len(self.ressources) >= val:
            self.ressources = self.ressources[:val]
        else :
            self.ressources = self.ressources + [1]*(val-len(self.ressources))

        self._reset_cell_infos()

    def _change_nbRess(self):
        self.ressources[self.current_cell] = self.findChild(QSpinBox, "nb_ress_spin").value()
        self._reset_text_cell_info()

    def _change_nbFam(self):
        self.familles = self.findChild(QSpinBox, "nb_fam").value()

    def _reset_cell_infos(self):
        self.findChild(QGroupBox, "cell_info_gbox").setTitle(f"Cellule {self.current_cell+1}")
        self.findChild(QSpinBox, "nb_ress_spin").setValue(self.ressources[self.current_cell])
        if self.current_cell == 0 :
            self.findChild(QPushButton, "cellule_prec").setEnabled(False)
        else :
            self.findChild(QPushButton, "cellule_prec").setEnabled(True)
        if self.current_cell == len(self.ressources)-1:
            self.findChild(QPushButton, "cellule_svt").setEnabled(False)
        else:
            self.findChild(QPushButton, "cellule_svt").setEnabled(True)
        self._reset_text_cell_info()
        
    def _reset_text_cell_info(self):
        txt_avant = str(self.ressources[:self.current_cell])[1:-1]
        in_txt = str(self.ressources[self.current_cell])
        txt_apres = str(self.ressources[self.current_cell+1:])[1:-1]

        if len(txt_apres) > 0:
            txt_apres = ", " + txt_apres
        if self.current_cell > 0:
            txt_avant = txt_avant + ", "

        txt = "["+txt_avant+'<font color="red">'+in_txt+'</font>'+txt_apres+"]"
        self.findChild(QLabel, "cells_info_lbl").setText(txt)

    def _preview_clic(self):
        s = systeme.systeme(self.ressources , self.familles)
        ecran = gui.gui(s)
        ecran.run()

    def _svt_click(self):
        self.findChild(QStackedWidget, "stackedWidget").setCurrentIndex(1)
        self._init_page(1)
        self.findChild(QPushButton, "btn_suivant").setText("Save config")
        self.findChild(QPushButton, "btn_suivant").clicked.disconnect()
        self.findChild(QPushButton, "btn_suivant").clicked.connect(self._save_config)
        
    def _prec_click(self):
        idx = self.findChild(QStackedWidget, "stackedWidget").currentIndex() -1
        if idx == -1 or idx == 1:
            self.setCurrentIndex(0)
        else :
            self.findChild(QStackedWidget, "stackedWidget").setCurrentIndex(idx)
        if idx == 0:
            self.findChild(QPushButton, "btn_suivant").setText("suivant")
            self.findChild(QPushButton, "btn_suivant").clicked.disconnect()
            self.findChild(QPushButton, "btn_suivant").clicked.connect(self._svt_click)
        
    def _save_config(self):
        #generate dic
        #json.dump(dic)
        fname , _ = QFileDialog.getSaveFileName(self, "sauvegarder configuration FMS", "", "*.json")
        print(fname)

    def _load_config(self):
        fname , _ = QFileDialog.getOpenFileName(self, "ouvrir configuration FMS", "", "*.json")
        print(fname)

    def _create_config(self):
        self.setCurrentIndex(1)

    def _init_page(self, index:int):
        if index == 1:
            self.current_cell_2 = 0
            self.current_famille = 0
            self.setup_times = [[0 for i in range(sum(self.ressources))] for j in range(self.familles)]
            self.process_times = [[0 for i in range(sum(self.ressources))] for j in range(self.familles)]
            self._disabilities_svt_prec_screen_2()
            self._disabilities_fam()
            self._reset_cell_text_2() 
            self._reset_grid()
            self._update_gbox_title_cell()
            self._update_gbox_title_fam()

    def _svt_second_cell_click(self):
        self.current_cell_2 +=1
        self._disabilities_svt_prec_screen_2()
        self._reset_cell_text_2()
        self._reset_grid()
        self._update_gbox_title_cell()

    def _prec_second_cell_click(self):
        self.current_cell_2 -=1
        self._disabilities_svt_prec_screen_2()
        self._reset_cell_text_2()
        self._reset_grid()
        self._update_gbox_title_cell()

    def _svt_fam_click(self):
        self.current_famille +=1
        self._disabilities_fam()
        self._reset_grid()
        self._update_gbox_title_fam()

    def _prec_fam_click(self):
        self.current_famille -=1
        self._disabilities_fam()
        self._reset_grid()
        self._update_gbox_title_fam()
    
    def _update_gbox_title_cell(self):
        self.findChild(QGroupBox, "gbox_cell_2").setTitle(f"Cellule : {self.current_cell_2+1}")

    def _update_gbox_title_fam(self):
        self.findChild(QGroupBox, "gbox_fam_2").setTitle(f'Famille : {self.current_famille+1} / {self.familles}')

    def _disabilities_fam(self):
        if self.current_famille == 0 :
            self.findChild(QPushButton, "fam_prec").setEnabled(False)
        else :
            self.findChild(QPushButton, "fam_prec").setEnabled(True)
        if self.current_famille == self.familles-1:
            self.findChild(QPushButton, "fam_svt").setEnabled(False)
        else:
            self.findChild(QPushButton, "fam_svt").setEnabled(True)

    def _disabilities_svt_prec_screen_2(self):
        if self.current_cell_2 == 0 :
            self.findChild(QPushButton, "cellule_prec_2").setEnabled(False)
        else :
            self.findChild(QPushButton, "cellule_prec_2").setEnabled(True)
        if self.current_cell_2 == len(self.ressources)-1:
            self.findChild(QPushButton, "cellule_svt_2").setEnabled(False)
        else:
            self.findChild(QPushButton, "cellule_svt_2").setEnabled(True)

    def _reset_cell_text_2(self):
        txt_avant = str(self.ressources[:self.current_cell_2])[1:-1]
        in_txt = str(self.ressources[self.current_cell_2])
        txt_apres = str(self.ressources[self.current_cell_2+1:])[1:-1]

        if len(txt_apres) > 0:
            txt_apres = ", " + txt_apres
        if self.current_cell_2 > 0:
            txt_avant = txt_avant + ", "

        txt = "["+txt_avant+'<font color="red">'+in_txt+'</font>'+txt_apres+"]"
        self.findChild(QLabel, "cells_info_lbl_2").setText(txt)

    def _reset_grid(self):
        layout = self.findChild(QGridLayout, "gridLayout") 
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().deleteLater()
        lbl1, lbl2, lbl3 = QLabel(text="Ressources"), QLabel(text="Temps setup"), QLabel(text="Temps traîtement")
        lbl1.setAlignment(QtCore.Qt.AlignCenter), lbl2.setAlignment(QtCore.Qt.AlignCenter), lbl3.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(lbl1, 0, 0)
        layout.addWidget(lbl2, 0, 1)
        layout.addWidget(lbl3, 0, 2)

        for i in range(self.ressources[self.current_cell_2]):
            qs = QSpinBox()
            qs.setValue(self.setup_times[self.current_famille][sum(self.ressources[:self.current_cell_2])+i])
            qs.valueChanged.connect(partial(self.update_setup, i)) , qs.setObjectName(f"spinbox_setup_{i}"), qs.setAlignment(QtCore.Qt.AlignCenter)
            qs2 = QSpinBox()
            qs2.setValue(self.process_times[self.current_famille][sum(self.ressources[:self.current_cell_2])+i])
            qs2.valueChanged.connect(partial(self.update_process, i)) , qs2.setObjectName(f"spinbox_process_{i}"), qs2.setAlignment(QtCore.Qt.AlignCenter)
            lbl = QLabel(text=f"R{sum(self.ressources[:self.current_cell_2]) +1 +i}")
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            layout.addWidget(lbl, i+1, 0)
            layout.addWidget(qs, i+1, 1)
            layout.addWidget(qs2, i+1, 2)

    def update_setup(self, i):
        print(f"spinbox_setup_{i}")
        self.setup_times[self.current_famille][sum(self.ressources[:self.current_cell_2])+i] = self.findChild(QSpinBox, f"spinbox_setup_{i}").value()
        print(self.setup_times, self.process_times)
    
    def update_process(self, i):
        self.process_times[self.current_famille][sum(self.ressources[:self.current_cell_2])+i] = self.findChild(QSpinBox, f"spinbox_process_{i}").value()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())