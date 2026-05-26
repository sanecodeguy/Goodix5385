import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Window 2.15

ApplicationWindow {
    id: root
    width: 1
    height: 1
    visible: true
    opacity: 0
    flags: Qt.Window | Qt.FramelessWindowHint | Qt.WindowTransparentForInput

    property bool deviceAvailable: false
    property string statusMessage: "Initializing..."

    signal requestEnroll(string finger)
    signal requestVerify()
    signal requestStop()

    Window {
        id: fingerDialog
        objectName: "fingerDialog"
        title: "Select Finger"
        width: 320
        height: 460
        visible: false
        flags: Qt.WindowStaysOnTopHint | Qt.Dialog
        color: "#1e1e2e"

        onVisibleChanged: {
            if (visible) {
                x = (Screen.width - width) / 2
                y = (Screen.height - height) / 2
            }
        }

        Column {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12

            Text {
                text: "Select Finger"
                color: "#cdd6f4"
                font.pixelSize: 16
                font.weight: Font.DemiBold
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Rectangle { width: parent.width; height: 1; color: "#313244" }

            Text {
                text: "Choose which finger to enroll:"
                color: "#a6adc8"
                font.pixelSize: 12
            }

            ScrollView {
                width: parent.width
                height: 260
                clip: true

                Column {
                    spacing: 4
                    Repeater {
                        model: [
                            "right-index-finger", "left-index-finger",
                            "right-middle-finger", "left-middle-finger",
                            "right-ring-finger", "left-ring-finger",
                            "right-little-finger", "left-little-finger",
                            "right-thumb", "left-thumb",
                        ]
                        delegate: RadioButton {
                            text: modelData.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())
                            checked: index === 0
                            onCheckedChanged: {
                                if (checked) fingerDialog.selectedFinger = modelData
                            }
                            contentItem: Text {
                                text: parent.text
                                color: "#cdd6f4"
                                font.pixelSize: 12
                                leftPadding: 8
                            }
                            indicator: Rectangle {
                                width: 16; height: 16; radius: 8
                                color: "transparent"
                                border.color: parent.checked ? "#89b4fa" : "#6c7086"
                                border.width: 2
                                Rectangle {
                                    anchors.centerIn: parent
                                    width: 8; height: 8; radius: 4
                                    color: "#89b4fa"
                                    visible: parent.parent.checked
                                }
                            }
                        }
                    }
                }
            }

            Item { width: 1; height: 1 }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 16

                Button {
                    text: "Cancel"
                    contentItem: Text {
                        text: parent.text; color: "#f38ba8"; font.pixelSize: 13
                    }
                    background: Rectangle {
                        color: parent.hovered ? "#2a1e24" : "transparent"
                        radius: 8; implicitWidth: 90; implicitHeight: 34
                    }
                    onClicked: { fingerDialog.visible = false; overlay.hide() }
                }
                Button {
                    text: "Start"
                    contentItem: Text {
                        text: parent.text; color: "#a6e3a1"; font.pixelSize: 13
                    }
                    background: Rectangle {
                        color: parent.hovered ? "#1e2a1e" : "transparent"
                        border.color: "#a6e3a1"; border.width: 1
                        radius: 8; implicitWidth: 90; implicitHeight: 34
                    }
                    onClicked: {
                        overlay.reset()
                        overlay.isEnrolling = true
                        overlay.fingerName = fingerDialog.selectedFinger.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())
                        root.requestEnroll(fingerDialog.selectedFinger)
                        fingerDialog.visible = false
                        overlay.show()
                    }
                }
            }
        }

        property string selectedFinger: "right-index-finger"
    }

    FingerprintOverlay {
        objectName: "overlay"
        onCancel: {
            root.requestStop()
            overlay.hide()
        }
    }

    Connections {
        target: root
        function onRequestEnroll(finger) { fprintBridge.on_enroll(finger) }
        function onRequestVerify() { fprintBridge.on_verify() }
        function onRequestStop() { fprintBridge.on_stop() }
    }
}
