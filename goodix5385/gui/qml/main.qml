import QtQuick 2.15
import QtQuick.Controls 2.15

ApplicationWindow {
    id: root
    width: 600
    height: 500
    visible: false
    color: "#1e1e2e"
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    modality: Qt.ApplicationModal

    property bool deviceAvailable: false
    property string statusMessage: "Initializing..."

    signal requestEnroll(string finger)
    signal requestVerify()
    signal requestStop()

    SystemTrayIcon {
        visible: true
        iconSource: "icons/fingerprint.svg"
        tooltip: "Goodix5385 Fingerprint"

        menu: Menu {
            MenuItem {
                text: "Enroll Fingerprint"
                onTriggered: {
                    fingerDialog.open()
                }
            }
            MenuItem {
                text: "Verify Fingerprint"
                onTriggered: {
                    root.requestVerify()
                    overlay.reset()
                    overlay.isEnrolling = false
                    overlay.show()
                }
            }
            MenuSeparator {}
            MenuItem {
                text: "Quit"
                onTriggered: Qt.quit()
            }
        }
    }

    Dialog {
        id: fingerDialog
        title: "Select Finger"
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true
        x: (parent.width - width) / 2
        y: (parent.height - height) / 2

        contentItem: Column {
            spacing: 12
            padding: 16

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
                RadioButton {
                    text: modelData.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())
                    checked: index === 0
                    onCheckedChanged: {
                        if (checked) fingerDialog.selectedFinger = modelData
                    }
                }
            }
        }
        property string selectedFinger: "right-index-finger"

        onAccepted: {
            root.requestEnroll(selectedFinger)
            overlay.reset()
            overlay.isEnrolling = true
            overlay.fingerName = selectedFinger.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())
            overlay.show()
        }
    }

    FingerprintOverlay {
        id: overlay
        onCancel: {
            root.requestStop()
            overlay.hide()
        }
        onStartEnroll: function(finger) {
            root.requestEnroll(finger)
        }
        onStartVerify: {
            root.requestVerify()
        }
    }

    Text {
        anchors.centerIn: parent
        text: root.statusMessage
        color: "#6c7086"
        font.pixelSize: 14
        visible: !deviceAvailable
    }
}
