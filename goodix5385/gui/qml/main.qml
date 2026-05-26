import QtQuick 2.15
import QtQuick.Controls 2.15

ApplicationWindow {
    id: root
    width: 480
    height: 520
    visible: false
    color: "transparent"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput
    modality: Qt.NonModal

    property bool deviceAvailable: false
    property string statusMessage: "Initializing..."

    signal requestEnroll(string finger)
    signal requestVerify()
    signal requestStop()
    signal showWindow()

    Dialog {
        id: fingerDialog
        objectName: "fingerDialog"
        title: "Select Finger"
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true
        x: Math.max(0, (parent.width - width) / 2)
        y: Math.max(0, (parent.height - height) / 2)
        width: 300
        height: 400

        contentItem: Column {
            spacing: 8
            padding: 12
            topPadding: 0

            Text {
                text: "Choose which finger to enroll:"
                color: "#cdd6f4"
                font.pixelSize: 13
                padding: 8
            }

            Column {
                spacing: 4
                Repeater {
                    model: [
                        "right-index-finger",
                        "left-index-finger",
                        "right-middle-finger",
                        "left-middle-finger",
                        "right-ring-finger",
                        "left-ring-finger",
                        "right-little-finger",
                        "left-little-finger",
                        "right-thumb",
                        "left-thumb",
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
                            id: ind
                            x: 0
                            y: (parent.height - height) / 2
                            width: 16; height: 16; radius: 8
                            color: "transparent"
                            border.color: ind.parent.checked ? "#89b4fa" : "#6c7086"
                            border.width: 2
                            Rectangle {
                                anchors.centerIn: parent
                                width: 8; height: 8; radius: 4
                                color: "#89b4fa"
                                visible: ind.parent.checked
                            }
                        }
                    }
                }
            }
        }

        background: Rectangle {
            color: "#1e1e2e"
            border.color: "#313244"
            radius: 12
        }

        header: Rectangle {
            color: "#181825"
            height: 40
            radius: 12

            Text {
                text: "Select Finger"
                color: "#cdd6f4"
                font.pixelSize: 15
                font.weight: Font.DemiBold
                anchors.centerIn: parent
            }
        }

        footer: Rectangle {
            color: "#181825"
            height: 48
            radius: 12

            Row {
                anchors.centerIn: parent
                spacing: 12

                Button {
                    text: "Cancel"
                    contentItem: Text {
                        text: parent.text
                        color: "#f38ba8"
                        font.pixelSize: 13
                    }
                    background: Rectangle {
                        color: parent.hovered ? "#2a1e24" : "transparent"
                        radius: 8
                        implicitWidth: 80; implicitHeight: 32
                    }
                    onClicked: fingerDialog.reject()
                }

                Button {
                    text: "Start"
                    contentItem: Text {
                        text: parent.text
                        color: "#a6e3a1"
                        font.pixelSize: 13
                    }
                    background: Rectangle {
                        color: parent.hovered ? "#1e2a1e" : "transparent"
                        border.color: "#a6e3a1"
                        border.width: 1
                        radius: 8
                        implicitWidth: 80; implicitHeight: 32
                    }
                    onClicked: fingerDialog.accept()
                }
            }
        }

        property string selectedFinger: "right-index-finger"

        onAccepted: {
            overlay.reset()
            overlay.isEnrolling = true
            overlay.fingerName = selectedFinger.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())
            root.requestEnroll(selectedFinger)
            overlay.show()
        }
        onRejected: {
            overlay.hide()
        }
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

    Shortcut {
        sequence: "Escape"
        onActivated: {
            if (overlay.visible) {
                root.requestStop()
                overlay.hide()
            }
        }
    }
}
