import logging
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Set

import pkg_resources
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import QEvent
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QActionGroup,
    QCompleter,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMessageBox,
)

from ..control.config_manager import config
#from ..control.pcd_manager import PointCloudManger

from ..labeling_strategies import PickingStrategy, PickingStrategy_s, OnePointStrategy, SpanningStrategy, PolyStrategy, PickingStrategy_small, PickingStrategy_mid, PickingStrategy_big
from .settings_dialog import SettingsDialog  # type: ignore
from .status_manager import StatusManager
from .viewer import GLWidget

if TYPE_CHECKING:
    from ..control.controller import Controller

def string_is_float(string: str, recect_negative: bool = False) -> bool:
    """Returns True if string can be converted to float"""
    try:
        decimal = float(string)
    except ValueError:
        return False
    if recect_negative and decimal < 0:
        return False
    return True


def set_floor_visibility(state: bool) -> None:
    #logging.info("%s floor grid (SHOW_FLOOR: %s).", "Activated" if state else "Deactivated",state,)
    config.set("USER_INTERFACE", "show_floor", str(state))


def set_orientation_visibility(state: bool) -> None:
    config.set("USER_INTERFACE", "show_orientation", str(state))


def set_zrotation_only(state: bool) -> None:
    config.set("USER_INTERFACE", "z_rotation_only", str(state))


def set_keep_perspective(state: bool) -> None:
    config.set("USER_INTERFACE", "keep_perspective", str(state))


# CSS file paths need to be set dynamically
STYLESHEET = """
    * {{
        background-color: #FFF;
        font-family: "DejaVu Sans", Arial;
    }}

    QMenu::item:selected {{
        background-color: rgb(255, 0, 0);
    }}

    QListWidget#label_list::item {{
        padding-left: 22px;
        padding-top: 7px;
        padding-bottom: 7px;
        background: url("{icons_dir}/cube-outline.svg") center left no-repeat;
    }}

    QListWidget#label_list::item:selected {{
        color: #FFF;
        border: none;
        background: rgb(255, 0, 0);
        background: url("{icons_dir}/cube-outline_white.svg") center left no-repeat, rgb(255, 0, 0);
    }}

    QComboBox#current_class_dropdown::item:checked{{
        color: gray;
    }}

    QComboBox#current_class_dropdown::item:selected {{
        color: #FFFFFF;
    }}

    QComboBox#current_class_dropdown{{
        selection-background-color: rgb(255, 0, 0);
    }}
"""


class GUI(QtWidgets.QMainWindow):
    def __init__(self, control: "Controller") -> None:
        
        #logging.info("GUI init...")
        
        super(GUI, self).__init__()
        uic.loadUi(
            pkg_resources.resource_filename(
                "labelCloud.resources.interfaces", "interface.ui"
            ),
            self,
        )
        self.resize(1500, 900)
        self.setWindowTitle("labelCloud")
        self.setStyleSheet(
            STYLESHEET.format(
                icons_dir=str(
                    Path(__file__)
                    .resolve()
                    .parent.parent.joinpath("resources")
                    .joinpath("icons")
                )
            )
        )

        # MENU BAR
        # File
        self.act_set_pcd_folder: QtWidgets.QAction
        self.act_set_label_folder: QtWidgets.QAction

        # Labels
        self.act_delete_all_labels: QtWidgets.QAction
        self.act_set_default_class: QtWidgets.QMenu
        self.actiongroup_default_class = QActionGroup(self.act_set_default_class)

        # Settings
        self.act_z_rotation_only: QtWidgets.QAction
        self.act_show_floor: QtWidgets.QAction
        self.act_show_orientation: QtWidgets.QAction
        self.act_save_perspective: QtWidgets.QAction
        self.act_align_pcd: QtWidgets.QAction
        self.act_change_settings: QtWidgets.QAction

        # STATUS BAR
        self.status_bar: QtWidgets.QStatusBar
        self.status_manager = StatusManager(self.status_bar)

        # CENTRAL WIDGET
        self.gl_widget: GLWidget
        #self.gl_widget2: GLWidget

        # LEFT PANEL
        # point cloud management
        self.label_current_pcd: QtWidgets.QLabel
        self.button_prev_pcd: QtWidgets.QPushButton
        self.button_next_pcd: QtWidgets.QPushButton
        self.button_set_pcd: QtWidgets.QPushButton
        self.progressbar_pcds: QtWidgets.QProgressBar

        # bbox control section
        self.button_bbox_up: QtWidgets.QPushButton
        self.button_bbox_down: QtWidgets.QPushButton
        self.button_bbox_left: QtWidgets.QPushButton
        self.button_bbox_right: QtWidgets.QPushButton
        self.button_bbox_forward: QtWidgets.QPushButton
        self.button_bbox_backward: QtWidgets.QPushButton
        self.dial_bbox_z_rotation: QtWidgets.QDial
        
        #self.button_bbox_decrease_dimension: QtWidgets.QPushButton
        #self.button_bbox_increase_dimension: QtWidgets.QPushButton

        # 2d image viewer
        self.button_show_image: QtWidgets.QPushButton
        self.button_show_image.setVisible(
            config.getboolean("USER_INTERFACE", "show_2d_image")
        )
        
        
        # label mode selection
        self.button_reload: QtWidgets.QPushButton
        #self.button_pick_bbox: QtWidgets.QPushButton
        self.button_pick_bbox_small: QtWidgets.QPushButton
        self.button_pick_bbox_mid: QtWidgets.QPushButton
        self.button_pick_bbox_big: QtWidgets.QPushButton
        #self.button_pick_bbox_s: QtWidgets.QPushButton
        #self.button_one_point: QtWidgets.QPushButton
        #self.button_span_bbox: QtWidgets.QPushButton
        #self.button_poly_bbox: QtWidgets.QPushButton
        
        self.button_save_label: QtWidgets.QPushButton

        # RIGHT PANEL
        self.label_list: QtWidgets.QListWidget
        self.edit_current_class: QtWidgets.QLineEdit
        self.button_deselect_label: QtWidgets.QPushButton
        self.button_delete_label: QtWidgets.QPushButton
        
        
        self.button_start: QtWidgets.QPushButton
        self.button_finished: QtWidgets.QPushButton
        
        

        self.button_class1: QtWidgets.QPushButton
        self.button_class2: QtWidgets.QPushButton
        self.button_class3: QtWidgets.QPushButton
        self.button_class4: QtWidgets.QPushButton
        self.button_class5: QtWidgets.QPushButton
        self.button_class6: QtWidgets.QPushButton     
        self.button_class7: QtWidgets.QPushButton
        self.button_class8: QtWidgets.QPushButton
        self.button_class9: QtWidgets.QPushButton
        self.button_class10: QtWidgets.QPushButton
        self.button_class11: QtWidgets.QPushButton
        self.button_class12: QtWidgets.QPushButton   
        """        
        self.button_class5: QtWidgets.QPushButton
        #self.button_class6: QtWidgets.QPushButton
        self.button_class7: QtWidgets.QPushButton
        #self.button_class8: QtWidgets.QPushButton
        #self.button_class9: QtWidgets.QPushButton
 
        self.button_transparency: QtWidgets.QPushButton

        self.button_fix_perspective: QtWidgets.QPushButton
        self.button_fix_perspective1: QtWidgets.QPushButton
        self.button_fix_perspective2: QtWidgets.QPushButton
        self.button_fix_perspective3: QtWidgets.QPushButton
        """

        # BOUNDING BOX PARAMETER EDITS
        self.edit_pos_x: QtWidgets.QLineEdit
        self.edit_pos_y: QtWidgets.QLineEdit
        self.edit_pos_z: QtWidgets.QLineEdit

        self.edit_length: QtWidgets.QLineEdit
        self.edit_width: QtWidgets.QLineEdit
        self.edit_height: QtWidgets.QLineEdit

        self.edit_rot_x: QtWidgets.QLineEdit
        self.edit_rot_y: QtWidgets.QLineEdit
        self.edit_rot_z: QtWidgets.QLineEdit

        self.all_line_edits = [
            self.edit_current_class,
            self.edit_pos_x,
            self.edit_pos_y,
            self.edit_pos_z,
            self.edit_length,
            self.edit_width,
            self.edit_height,
            self.edit_rot_x,
            self.edit_rot_y,
            self.edit_rot_z,
        ]

        self.label_volume: QtWidgets.QLabel

        # Connect with controller
        self.controller = control
        self.controller.startup(self)

        # Connect all events to functions
        self.connect_events()
        self.set_checkbox_states()  # tick in menu
        self.update_label_completer()  # initialize label completer with classes in config
        self.update_default_object_class_menu()

        # Start event cycle
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(20)  # period, in milliseconds
        self.timer.timeout.connect(self.controller.loop_gui)
        self.timer.start()
        
        
        self.timer2 = QtCore.QTimer(self)
        self.timer2.setInterval(1000*5)  # period, in milliseconds
        self.timer2.timeout.connect(self.controller.save)
        self.timer2.start()
        
        self.timer3 = QtCore.QTimer(self)
        self.timer3.setInterval(1000*4*60)  # period, in milliseconds
        self.timer3.timeout.connect(self.controller.timeOutFunc)
        #self.timer3.start()

        
        

    # Event connectors
    def connect_events(self) -> None:
        # POINTCLOUD CONTROL
        self.button_next_pcd.clicked.connect(
            lambda: self.controller.next_pcd(save=True)
        )
        self.button_prev_pcd.clicked.connect(self.controller.prev_pcd)

        # BBOX CONTROL
        self.button_bbox_up.pressed.connect(
            #lambda: self.controller.bbox_controller.translate_along_z()
            self.controller.button_bbox_up
        )
        self.button_bbox_down.pressed.connect(
            #lambda: self.controller.bbox_controller.translate_along_z(down=True)
            self.controller.button_bbox_down
        )
        self.button_bbox_left.pressed.connect(
            #lambda: self.controller.bbox_controller.translate_along_x(left=True)
            self.controller.button_bbox_left
        )
        self.button_bbox_right.pressed.connect(
            #lambda: self.controller.bbox_controller.translate_along_x
            self.controller.button_bbox_right
        )
        self.button_bbox_forward.pressed.connect(
            #lambda: self.controller.bbox_controller.translate_along_y(forward=True)
            self.controller.button_bbox_forward
        )
        
        self.button_bbox_backward.pressed.connect(
            #lambda: self.controller.bbox_controller.translate_along_y()
            self.controller.button_bbox_backward
        )
        
        self.button_set_pcd.pressed.connect(lambda: self.ask_custom_index())
        
        

        self.dial_bbox_z_rotation.valueChanged.connect(
            lambda x: self.controller.bbox_controller.rotate_around_z(x, absolute=True)
            #self.controller.dial_bbox_z_rotation(x)
        )
        """
        self.button_bbox_decrease_dimension.clicked.connect(
            #lambda: self.controller.bbox_controller.scale(decrease=True)bel_list
            self.controller.button_bbox_decrease_dimension
        )
        self.button_bbox_increase_dimension.clicked.connect(
            #lambda: self.controller.bbox_controller.scale()
            self.controller.button_bbox_increase_dimension
        )
        """

        # LABELING CONTROL
        self.edit_current_class.textChanged.connect(
            self.controller.bbox_controller.set_classname
            #self.controller.edit_current_class
        )
        self.button_deselect_label.clicked.connect(
            #self.controller.bbox_controller.deselect_bbox  
            self.controller.button_deselect_label
        )
        self.button_delete_label.clicked.connect(
            #self.controller.bbox_controller.delete_current_bbox
            self.controller.button_delete_label
        )
        
        self.label_list.currentRowChanged.connect(
            self.controller.bbox_controller.set_active_bbox
        )
        self.button_start.clicked.connect(
            #self.controller.bbox_controller.delete_current_bbox
            self.controller.button_start
        )

        self.button_finished.clicked.connect(
            #self.controller.bbox_controller.delete_current_bbox
            self.controller.button_finished
        )


        self.button_class1.clicked.connect(
            #self.controller.bbox_controller.delete_current_bbox
            self.controller.button_class1
        )
        self.button_class2.clicked.connect(
            #self.controller.bbox_controller.delete_current_bbox
            self.controller.button_class2
        )
        self.button_class3.clicked.connect(
            #self.controller.bbox_controller.delete_current_bbox
            self.controller.button_class3
        )
        self.button_class4.clicked.connect(
            #self.controller.bbox_controller.delete_current_bbox
            self.controller.button_class4
        )
        self.button_class5.clicked.connect(
            #self.controller.bbox_controller.delete_current_bbox
            self.controller.button_class5
        )
        self.button_class6.clicked.connect(
            #self.controller.bbox_controller.delete_current_bbox
            self.controller.button_class6
        )
        self.button_class7.clicked.connect(
            #self.controller.bbox_controller.delete_current_bbox
            self.controller.button_class7
        )
        self.button_class8.clicked.connect(
            #self.controller.bbox_controller.delete_current_bbox
            self.controller.button_class8
        )
        self.button_class9.clicked.connect(
            #self.controller.bbox_controller.delete_current_bbox
            self.controller.button_class9
        )
        self.button_class10.clicked.connect(
            #self.controller.bbox_controller.delete_current_bbox
            self.controller.button_class10
        )
        self.button_class11.clicked.connect(
            #self.controller.bbox_controller.delete_current_bbox
            self.controller.button_class11
        )
        self.button_class12.clicked.connect(
            #self.controller.bbox_controller.delete_current_bbox
            self.controller.button_class12
        )

        """
        # Make Transparency
        self.button_transparency.clicked.connect(
            #self.controller.loop_gui
        )
        """        
 
        """ 
        # Perspective CONTROL
        self.button_fix_perspective.clicked.connect(
            self.controller.start_mode.change_activation
        )
        
        # Perspective CONTROL
        self.button_fix_perspective1.clicked.connect(
            self.controller.pcd_manager.reset_rotation1
        )
        self.button_fix_perspective2.clicked.connect(
            self.controller.pcd_manager.reset_rotation2
        )
        self.button_fix_perspective3.clicked.connect(
            self.controller.pcd_manager.reset_rotation3
        )
        """ 

        # open_2D_img
        self.button_show_image.pressed.connect(lambda: self.show_2d_image())
        
        
        self.button_reload.clicked.connect(
            self.controller.reload
        )
        

        # LABEL CONTROL
        """
        self.button_pick_bbox.clicked.connect(

            self.controller.button_pick_bbox
        )
        """
        
        """
        self.button_pick_bbox.clicked.connect(

            lambda: self.controller.drawing_mode.set_drawing_strategy(
                PickingStrategy(self)
            )
        )
        """
        self.button_pick_bbox_small.clicked.connect(

            lambda: self.controller.drawing_mode.set_drawing_strategy(
                PickingStrategy_small(self)
            )
        )
        self.button_pick_bbox_mid.clicked.connect(

            lambda: self.controller.drawing_mode.set_drawing_strategy(
                PickingStrategy_mid(self)
            )
        )
        self.button_pick_bbox_big.clicked.connect(

            lambda: self.controller.drawing_mode.set_drawing_strategy(
                PickingStrategy_big(self)
            )
        )
        
        """
        self.button_pick_bbox_s.clicked.connect(
            lambda: self.controller.drawing_mode.set_drawing_strategy(
                PickingStrategy_s(self)
            )
        )
        self.button_one_point.clicked.connect(
            lambda: self.controller.drawing_mode.set_drawing_strategy(
                OnePointStrategy(self)
            )
        )
        """
        """
        self.button_span_bbox.clicked.connect(
            lambda: self.controller.drawing_mode.set_drawing_strategy(
                SpanningStrategy(self)
            )
        )
        """
        """
        self.button_poly_bbox.clicked.connect(
            lambda: self.controller.drawing_mode.set_drawing_strategy(
                PolyStrategy(self)
            )
        )
        """

        self.button_save_label.clicked.connect(self.controller.save)

        # BOUNDING BOX PARAMETER
        self.edit_pos_x.editingFinished.connect(
            lambda: self.update_bbox_parameter("pos_x")
        )
        self.edit_pos_y.editingFinished.connect(
            lambda: self.update_bbox_parameter("pos_y")
        )
        self.edit_pos_z.editingFinished.connect(
            lambda: self.update_bbox_parameter("pos_z")
        )

        self.edit_length.editingFinished.connect(
            lambda: self.update_bbox_parameter("length")
        )
        self.edit_width.editingFinished.connect(
            lambda: self.update_bbox_parameter("width")
        )
        self.edit_height.editingFinished.connect(
            lambda: self.update_bbox_parameter("height")
        )

        self.edit_rot_x.editingFinished.connect(
            lambda: self.update_bbox_parameter("rot_x")
        )
        self.edit_rot_y.editingFinished.connect(
            lambda: self.update_bbox_parameter("rot_y")
        )
        self.edit_rot_z.editingFinished.connect(
            lambda: self.update_bbox_parameter("rot_z")
        )

        # MENU BAR
        self.act_set_pcd_folder.triggered.connect(self.change_pointcloud_folder)
        self.act_set_label_folder.triggered.connect(self.change_label_folder)
        self.actiongroup_default_class.triggered.connect(
            self.change_default_object_class
        )
        self.act_delete_all_labels.triggered.connect(
            self.controller.bbox_controller.reset
        )
        self.act_z_rotation_only.toggled.connect(set_zrotation_only)
        self.act_show_floor.toggled.connect(set_floor_visibility)
        self.act_show_orientation.toggled.connect(set_orientation_visibility)
        self.act_save_perspective.toggled.connect(set_keep_perspective)
        self.act_align_pcd.toggled.connect(self.controller.align_mode.change_activation)
        self.act_change_settings.triggered.connect(self.show_settings_dialog)

    def set_checkbox_states(self) -> None:
        self.act_show_floor.setChecked(
            config.getboolean("USER_INTERFACE", "show_floor")
        )
        self.act_show_orientation.setChecked(
            config.getboolean("USER_INTERFACE", "show_orientation")
        )
        self.act_z_rotation_only.setChecked(
            config.getboolean("USER_INTERFACE", "z_rotation_only")
        )

    # Collect, filter and forward events to viewer
    def eventFilter(self, event_object, event) -> bool:
        # Keyboard Events
        # if (event.type() == QEvent.KeyPress) and (not self.line_edited_activated()):
        if (event.type() == QEvent.KeyPress) and (
            event_object == self
        ):  # TODO: Cleanup old filter
            self.controller.key_press_event(event)
            self.update_bbox_stats(self.controller.bbox_controller.get_active_bbox())
            return True  # TODO: Recheck pyqt behaviour
        elif event.type() == QEvent.KeyRelease:
            self.controller.key_release_event(event)

        # Mouse Events
        elif (event.type() == QEvent.MouseMove) and (event_object == self.gl_widget):
            self.controller.mouse_move_event(event)
            self.update_bbox_stats(self.controller.bbox_controller.get_active_bbox())
        elif (event.type() == QEvent.Wheel) and (event_object == self.gl_widget):
            self.controller.mouse_scroll_event(event)
            self.update_bbox_stats(self.controller.bbox_controller.get_active_bbox())
        elif event.type() == QEvent.MouseButtonDblClick and (
            event_object == self.gl_widget
        ):
            self.controller.mouse_double_clicked(event)
            return True
        elif (event.type() == QEvent.MouseButtonPress) and (
            event_object == self.gl_widget
        ):
            self.controller.mouse_clicked(event)
            self.update_bbox_stats(self.controller.bbox_controller.get_active_bbox())
        elif (event.type() == QEvent.MouseButtonPress) and (
            event_object != self.edit_current_class
        ):
            self.edit_current_class.clearFocus()
            self.update_bbox_stats(self.controller.bbox_controller.get_active_bbox())
        return False

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        #logging.info("Closing window after saving ...")
        self.controller.save()
        self.timer.stop()
        self.timer2.stop()
        a0.accept()

    def show_settings_dialog(self) -> None:
        dialog = SettingsDialog(self)
        dialog.exec()

    def show_2d_image(self):
        """Searches for a 2D image with the point cloud name and displays it in a new window."""
        image_folder = config.getpath("FILE", "image_folder")

        # Look for image files with the name of the point cloud
        pcd_name = self.controller.pcd_manager.pcd_path.stem
        image_file_pattern = re.compile(f"{pcd_name}+(\.(?i:(jpe?g|png|gif|bmp|tiff)))")

        try:
            image_name = next(
                filter(image_file_pattern.search, os.listdir(image_folder))
            )
        except StopIteration:
            QMessageBox.information(
                self,
                "No 2D Image File",
                (
                    f"Could not find a related image in the image folder ({image_folder}).\n"
                    "Check your path to the folder or if an image for this point cloud exists."
                ),
                QMessageBox.Ok,
            )
        else:
            image_path = image_folder.joinpath(image_name)
            image = QtGui.QImage(QtGui.QImageReader(str(image_path)).read())
            self.imageLabel = QLabel()
            self.imageLabel.setWindowTitle(f"2D Image ({image_name})")
            self.imageLabel.setPixmap(QPixmap.fromImage(image))
            self.imageLabel.show()

    def show_no_pointcloud_dialog(
        self, pcd_folder: Path, pcd_extensions: Set[str]
    ) -> None:
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setText(
            "<b>labelCloud could not find any valid point cloud files inside the "
            "specified folder.</b>"
        )
        msg.setInformativeText(
            f"Please copy all your point clouds into <code>{pcd_folder.resolve()}</code> or update "
            "the point cloud folder location. labelCloud supports the following point "
            f"cloud file formats:\n {', '.join(pcd_extensions)}."
        )
        msg.setWindowTitle("No Point Clouds Found")
        msg.exec_()

    # VISUALIZATION METHODS

    def set_pcd_label(self, pcd_name: str) -> None:
        self.label_current_pcd.setText("Current: <em>%s</em>" % pcd_name)

    def init_progress(self, min_value, max_value):
        self.progressbar_pcds.setMinimum(min_value)
        self.progressbar_pcds.setMaximum(max_value)

    def update_progress(self, value) -> None:
        self.progressbar_pcds.setValue(value)

    def update_curr_class_edit(self, force: str = None) -> None:
        if force is not None:
            self.edit_current_class.setText(force)
        else:
            bbox = self.controller.bbox_controller.get_active_bbox()
            if bbox:
                self.edit_current_class.setText(bbox.get_classname())

    def update_label_completer(self, classnames=None) -> None:
        if classnames is None:
            classnames = set()
        classnames.update(config.getlist("LABEL", "object_classes"))
        self.edit_current_class.setCompleter(QCompleter(classnames))

    def update_bbox_stats(self, bbox) -> None:
        viewing_precision = config.getint("USER_INTERFACE", "viewing_precision")
        if bbox and not self.line_edited_activated():
            self.edit_pos_x.setText(str(round(bbox.get_center()[0], viewing_precision)))
            self.edit_pos_y.setText(str(round(bbox.get_center()[1], viewing_precision)))
            self.edit_pos_z.setText(str(round(bbox.get_center()[2], viewing_precision)))

            self.edit_length.setText(
                str(round(bbox.get_dimensions()[0], viewing_precision))
            )
            self.edit_width.setText(
                str(round(bbox.get_dimensions()[1], viewing_precision))
            )
            self.edit_height.setText(
                str(round(bbox.get_dimensions()[2], viewing_precision))
            )

            self.edit_rot_x.setText(str(round(bbox.get_x_rotation(), 1)))
            self.edit_rot_y.setText(str(round(bbox.get_y_rotation(), 1)))
            self.edit_rot_z.setText(str(round(bbox.get_z_rotation(), 1)))

            self.label_volume.setText(str(round(bbox.get_volume(), viewing_precision)))

    def update_bbox_parameter(self, parameter: str) -> None:
        str_value = None
        self.setFocus()  # Changes the focus from QLineEdit to the window

        if parameter == "pos_x":
            str_value = self.edit_pos_x.text()
        if parameter == "pos_y":
            str_value = self.edit_pos_y.text()
        if parameter == "pos_z":
            str_value = self.edit_pos_z.text()
        if str_value and string_is_float(str_value):
            self.controller.bbox_controller.update_position(parameter, float(str_value))
            return

        if parameter == "length":
            str_value = self.edit_length.text()
        if parameter == "width":
            str_value = self.edit_width.text()
        if parameter == "height":
            str_value = self.edit_height.text()
        if str_value and string_is_float(str_value, recect_negative=True):
            self.controller.bbox_controller.update_dimension(
                parameter, float(str_value)
            )
            return

        if parameter == "rot_x":
            str_value = self.edit_rot_x.text()
        if parameter == "rot_y":
            str_value = self.edit_rot_y.text()
        if parameter == "rot_z":
            str_value = self.edit_rot_z.text()
        if str_value and string_is_float(str_value):
            #self.button_pick_bbox.setEnabled(state)
            self.controller.bbox_controller.update_rotation(parameter, float(str_value))
            return

    # Enables, disables the draw mode
    def activate_draw_modes(self, state: bool) -> None:
        #self.button_pick_bbox.setEnabled(state)
        self.button_pick_bbox_small.setEnabled(state)
        self.button_pick_bbox_mid.setEnabled(state)
        self.button_pick_bbox_big.setEnabled(state)
        #self.button_pick_bbox_s.setEnabled(state)
        #self.button_span_bbox.setEnabled(state)
        #self.button_poly_bbox.setEnabled(state)
        #True
        
    def line_edited_activated(self) -> bool:
        for line_edit in self.all_line_edits:
            if line_edit.hasFocus():
                return True
        return False

    def change_pointcloud_folder(self) -> None:
        path_to_folder = Path(
            QFileDialog.getExistingDirectory(
                self,
                "Change Point Cloud Folder",
                directory=config.get("FILE", "pointcloud_folder"),
            )
        )
        if not path_to_folder.is_dir():
            logging.warning("Please specify a valid folder path.")
        else:
            self.controller.pcd_manager.pcd_folder = path_to_folder
            self.controller.pcd_manager.read_pointcloud_folder()
            self.controller.pcd_manager.get_next_pcd()
            #logging.info("Changed point cloud folder to %s!" % path_to_folder)

    def change_label_folder(self) -> None:
        path_to_folder = Path(
            QFileDialog.getExistingDirectory(
                self,
                "Change Label Folder",
                directory=config.get("FILE", "label_folder"),
            )
        )
        if not path_to_folder.is_dir():
            logging.warning("Please specify a valid folder path.")
        else:
            self.controller.pcd_manager.label_manager.label_folder = path_to_folder
            self.controller.pcd_manager.label_manager.label_strategy.update_label_folder(
                path_to_folder
            )
            #logging.info("Changed label folder to %s!" % path_to_folder)

    def update_default_object_class_menu(self, new_classes: Set[str] = None) -> None:
        object_classes = {
            str(class_name) for class_name in config.getlist("LABEL", "object_classes")
        }
        object_classes.update(new_classes or [])
        existing_classes = {
            action.text() for action in self.actiongroup_default_class.actions()
        }
        for object_class in object_classes.difference(existing_classes):
            action = self.actiongroup_default_class.addAction(
                object_class
            )  # TODO: Add limiter for number of classes
            action.setCheckable(True)
            if object_class == config.get("LABEL", "std_object_class"):
                action.setChecked(True)

        self.act_set_default_class.addActions(self.actiongroup_default_class.actions())

    def change_default_object_class(self, action: QAction) -> None:
        config.set("LABEL", "std_object_class", action.text())
        #logging.info("Changed default object class to %s.", action.text())

    def ask_custom_index(self):
        input_d = QInputDialog(self)
        self.input_pcd = input_d
        input_d.setInputMode(QInputDialog.IntInput)
        input_d.setWindowTitle("labelCloud")
        input_d.setLabelText("Insert Point Cloud number: ()")
        input_d.setIntMaximum(len(self.controller.pcd_manager.pcds) - 1)
        input_d.intValueChanged.connect(lambda val: self.update_dialog_pcd(val))
        input_d.intValueSelected.connect(lambda val: self.controller.custom_pcd(val))
        input_d.open()
        self.update_dialog_pcd(0)

    def update_dialog_pcd(self, value: int) -> None:
        pcd_path = self.controller.pcd_manager.pcds[value]
        self.input_pcd.setLabelText(f"Insert Point Cloud number: {pcd_path.name}")
