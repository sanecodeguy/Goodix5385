import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Window 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    id: root
    width: 400
    height: 420
    visible: true
    flags: Qt.WindowStaysOnTopHint
    color: "#1e1e2e"
    title: "Fingerprint Scanner"
    minimumWidth: 380
    minimumHeight: 380

    property bool deviceAvailable: false
    property string statusMessage: "Initializing..."

    signal requestEnroll(string finger)
    signal requestVerify()
    signal requestStop()

    Rectangle {
        anchors.centerIn: parent
        width: parent.width - 40
        height: parent.height - 40
        radius: 24
        color: "#181825"
        border.color: "#313244"
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 32
            spacing: 16

            Item { Layout.fillHeight: true; width: 1 }

            // Icon
            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                width: 80; height: 80; radius: 40
                color: "#1e1e2e"
                border.color: "#89b4fa"
                border.width: 2

                Rectangle {
                    anchors.centerIn: parent
                    width: 36; height: 44
                    radius: 18
                    color: "transparent"
                    border.color: "#89b4fa"
                    border.width: 2
                }
                Rectangle {
                    anchors.centerIn: parent
                    width: 20; height: 12
                    radius: 10
                    color: "transparent"
                    border.color: "#89b4fa"
                    border.width: 2
                    anchors.verticalCenterOffset: 18
                }
            }

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "Fingerprint Scanner"
                color: "#cdd6f4"
                font.pixelSize: 20
                font.weight: Font.DemiBold
            }

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: statusMessage
                color: deviceAvailable ? "#a6e3a1" : "#f38ba8"
                font.pixelSize: 12
            }

            Item { Layout.fillHeight: true; width: 1 }

            GridLayout {
                Layout.fillWidth: true
                columns: 2
                columnSpacing: 16
                rowSpacing: 0

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 100
                    radius: 16
                    color: "#1e1e2e"
                    border.color: parent.containsMouse ? "#89b4fa" : "#313244"
                    border.width: 1

                    MouseArea {
                        id: enrollArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            fingerDialog.visible = true
                            fingerDialog.raise()
                            fingerDialog.requestActivate()
                        }
                    }

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 8

                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: "✚"
                            color: "#89b4fa"
                            font.pixelSize: 24
                        }
                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: "Enroll"
                            color: "#cdd6f4"
                            font.pixelSize: 14
                            font.weight: Font.DemiBold
                        }
                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: "Register new finger"
                            color: "#6c7086"
                            font.pixelSize: 11
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 100
                    radius: 16
                    color: "#1e1e2e"
                    border.color: parent.containsMouse ? "#a6e3a1" : "#313244"
                    border.width: 1

                    MouseArea {
                        id: verifyArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            overlay.reset()
                            overlay.isEnrolling = false
                            overlay.fingerName = ""
                            overlay.status = "Place your finger on the sensor"
                            overlay.scanCount = 0
                            root.requestVerify()
                            overlay.show()
                            overlay.raise()
                            overlay.requestActivate()
                        }
                    }

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 8

                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: "✓"
                            color: "#a6e3a1"
                            font.pixelSize: 24
                        }
                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: "Verify"
                            color: "#cdd6f4"
                            font.pixelSize: 14
                            font.weight: Font.DemiBold
                        }
                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: "Scan existing finger"
                            color: "#6c7086"
                            font.pixelSize: 11
                        }
                    }
                }
            }

            Button {
                Layout.alignment: Qt.AlignHCenter
                text: "Quit"
                flat: true
                contentItem: Text {
                    text: parent.text
                    color: "#6c7086"
                    font.pixelSize: 12
                }
                background: Rectangle {
                    color: parent.hovered ? "#2a1e24" : "transparent"
                    radius: 8
                    implicitWidth: 60; implicitHeight: 28
                }
                onClicked: Qt.quit()
            }

            Item { Layout.fillHeight: true; width: 1 }
        }
    }

    FingerprintOverlay {
        id: overlay
        objectName: "overlay"
        onCancel: {
            root.requestStop()
            overlay.hide()
        }
        onRetry: {
            overlay.reset()
            root.requestVerify()
            overlay.show()
            overlay.raise()
            overlay.requestActivate()
        }
    }

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
                selectedFinger = "right-index-finger"
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
                    onClicked: fingerDialog.visible = false
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
                        overlay.raise()
                        overlay.requestActivate()
                    }
                }
            }
        }

        property string selectedFinger: "right-index-finger"
    }

    Connections {
        target: root
        function onRequestEnroll(finger) { fprintBridge.on_enroll(finger) }
        function onRequestVerify() { fprintBridge.on_verify() }
        function onRequestStop() { fprintBridge.on_stop() }
    }
}
