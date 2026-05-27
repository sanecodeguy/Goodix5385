import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Window 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    id: root
    width: 340
    height: 380
    visible: true
    flags: Qt.WindowStaysOnTopHint
    color: "#07070d"
    title: "Goodix 5385"
    minimumWidth: 320
    minimumHeight: 340

    property bool deviceAvailable: false
    property string statusMessage: "Initializing..."

    signal requestEnroll(string finger)
    signal requestVerify(string finger)
    signal requestStop()
    signal requestDelete(string finger)

    // ── Background gradient ──────────────────────────────────────────────────
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0a0a14" }
            GradientStop { position: 1.0; color: "#07070d" }
        }
    }

    // Subtle top accent line
    Rectangle {
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        width: 120; height: 1
        color: "#89b4fa30"
        radius: 1
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 32
        spacing: 0

        // ── Header ───────────────────────────────────────────────────────────
        Text {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 6
            text: "Goodix 5385 Fingerprint"
            color: "#c8cfe8"
            font.pixelSize: 15
            font.weight: Font.Light
            font.letterSpacing: 1.8
        }

        // Device status dot + text
        Row {
            Layout.alignment: Qt.AlignHCenter
            spacing: 6

            Rectangle {
                width: 5; height: 5; radius: 2.5
                anchors.verticalCenter: parent.verticalCenter
                color: deviceAvailable ? "#a6e3a1" : "#f38ba8"

                SequentialAnimation on opacity {
                    running: deviceAvailable
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.3; duration: 1000 }
                    NumberAnimation { to: 1.0; duration: 1000 }
                }
            }

            Text {
                text: statusMessage
                color: deviceAvailable ? "#555c6e" : "#5a3040"
                font.pixelSize: 10
                font.letterSpacing: 0.4
            }
        }

        Item { Layout.fillHeight: true }

        // ── Action cards ──────────────────────────────────────────────────────
        Row {
            Layout.alignment: Qt.AlignHCenter
            spacing: 14

            // Enroll card
            ActionCard {
                width: 130; height: 110
                accentColor: "#89b4fa"
                iconText: "+"
                label: "Enroll"
                sublabel: "Register finger"
                onActivated: {
                    fingerDialog.dialogMode = "enroll"
                    fingerDialog.title = "Enroll Finger"
                    fingerDialog.prompt = "Choose which finger to enroll:"
                    fingerDialog.actionText = "Start Enroll"
                    fingerDialog.visible = true
                    fingerDialog.raise()
                    fingerDialog.requestActivate()
                }
            }

            // Verify card
            ActionCard {
                width: 130; height: 110
                accentColor: "#a6e3a1"
                iconText: "✓"
                label: "Verify"
                sublabel: "Scan finger"
                onActivated: {
                    if (fingerDialog.enrolledFingers.length === 1) {
                        // Only one finger — verify it directly
                        overlay.reset()
                        overlay.isEnrolling = false
                        overlay.fingerName = fingerDialog.enrolledFingers[0]
                            .replace(/-/g, " ")
                            .replace(/\b\w/g, function(c){ return c.toUpperCase() })
                        overlay.status = "Place your finger on the sensor"
                        overlay.scanCount = 0
                        root.requestVerify(fingerDialog.enrolledFingers[0])
                        overlay.show()
                        overlay.raise()
                        overlay.requestActivate()
                    } else {
                        // Multiple fingers — let user pick
                        fingerDialog.dialogMode = "verify"
                        fingerDialog.title = "Verify Finger"
                        fingerDialog.prompt = "Choose which finger to scan:"
                        fingerDialog.actionText = "Start Verify"
                        fingerDialog.visible = true
                        fingerDialog.raise()
                        fingerDialog.requestActivate()
                    }
                }
            }
        }

        Item { Layout.fillHeight: true; Layout.maximumHeight: 12 }

        // ── Delete strip ──────────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            height: 40
            radius: 12
            color: deleteMouse.containsMouse ? "#180a0c" : "transparent"
            border.color: deleteMouse.containsMouse ? "#f38ba860" : "#2a2a3e"
            border.width: 1.5

            Behavior on color       { ColorAnimation { duration: 150 } }
            Behavior on border.color{ ColorAnimation { duration: 150 } }

            Row {
                anchors.centerIn: parent
                spacing: 8
                Text { text: "✕"; color: "#f38ba8"; font.pixelSize: 11; anchors.verticalCenter: parent.verticalCenter }
                Text { text: "Delete fingerprint"; color: "#f38ba8"; font.pixelSize: 12; font.letterSpacing: 0.3; anchors.verticalCenter: parent.verticalCenter }
            }

            MouseArea {
                id: deleteMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    fingerDialog.dialogMode = "delete"
                    fingerDialog.title = "Delete Fingerprint"
                    fingerDialog.prompt = "Select fingerprint to remove:"
                    fingerDialog.actionText = "Delete"
                    fingerDialog.visible = true
                    fingerDialog.raise()
                    fingerDialog.requestActivate()
                }
            }
        }

        Item { Layout.fillHeight: true; Layout.maximumHeight: 16 }

        // ── Quit ──────────────────────────────────────────────────────────────
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "quit"
            color: quitMouse.containsMouse ? "#555870" : "#353748"
            font.pixelSize: 11
            font.letterSpacing: 1.5
            Behavior on color { ColorAnimation { duration: 120 } }

            MouseArea {
                id: quitMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: Qt.quit()
            }
        }

        Item { Layout.fillHeight: true; Layout.maximumHeight: 4 }
    }

    // ── Reusable action card component ────────────────────────────────────────
    component ActionCard: Rectangle {
        id: card
        radius: 16
        color: cardMouse.containsMouse ? Qt.lighter("#0f1020", 1.35) : "#0f1020"
        border.color: cardMouse.containsMouse ? Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.55) : "#2a2a3e"
        border.width: 1.5

        property color accentColor: "#89b4fa"
        property string iconText: ""
        property string label: ""
        property string sublabel: ""
        signal activated()

        Behavior on color       { ColorAnimation { duration: 150 } }
        Behavior on border.color{ ColorAnimation { duration: 150 } }

        Column {
            anchors.centerIn: parent
            spacing: 6

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: card.iconText
                color: Qt.rgba(card.accentColor.r, card.accentColor.g, card.accentColor.b, 0.95)
                font.pixelSize: 24
                font.weight: Font.Light
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: card.label
                color: "#e8eaf6"
                font.pixelSize: 15
                font.weight: Font.Medium
                font.letterSpacing: 0.3
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: card.sublabel
                color: "#555870"
                font.pixelSize: 11
                font.letterSpacing: 0.3
            }
        }

        MouseArea {
            id: cardMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: card.activated()
        }
    }

    // ── Overlay window ─────────────────────────────────────────────────────────
    FingerprintOverlay {
        id: overlay
        objectName: "overlay"
        onCancel: {
            root.requestStop()
            overlay.hide()
        }
    }

    // ── Finger picker dialog ───────────────────────────────────────────────────
    Window {
        id: fingerDialog
        objectName: "fingerDialog"
        title: "Select Finger"
        width: 300
        height: 440
        visible: false
        flags: Qt.WindowStaysOnTopHint | Qt.Dialog
        color: "#07070d"

        property string selectedFinger: "right-index-finger"
        property string dialogMode: "enroll"
        property string prompt: ""
        property string actionText: "Confirm"
        property var enrolledFingers: []

        onVisibleChanged: {
            if (visible) {
                x = (Screen.width  - width)  / 2
                y = (Screen.height - height) / 2
                selectedFinger = "right-index-finger"
            }
        }

        Rectangle {
            anchors.fill: parent
            color: "#07070d"

            Column {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 14

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: fingerDialog.title
                    color: "#c8cfe8"
                    font.pixelSize: 15
                    font.weight: Font.Medium
                    font.letterSpacing: 0.5
                }

                Rectangle { width: parent.width; height: 1; color: "#151525" }

                Text {
                    text: fingerDialog.prompt
                    color: "#353748"
                    font.pixelSize: 11
                    font.letterSpacing: 0.2
                }

                ScrollView {
                    width: parent.width
                    height: 240
                    clip: true

                    Column {
                        width: parent.width
                        spacing: 3

                        Repeater {
                            model: fingerDialog.dialogMode === "delete"
                                   || fingerDialog.dialogMode === "verify"
                                   ? fingerDialog.enrolledFingers
                                   : ["right-index-finger","left-index-finger",
                                      "right-middle-finger","left-middle-finger",
                                      "right-ring-finger","left-ring-finger",
                                      "right-little-finger","left-little-finger",
                                      "right-thumb","left-thumb"]

                            delegate: Rectangle {
                                width: parent.width
                                height: 34
                                radius: 8
                                color: fingerDialog.selectedFinger === modelData
                                       ? "#0f1828"
                                       : (rowHover.containsMouse ? "#0c0c1a" : "transparent")
                                border.color: fingerDialog.selectedFinger === modelData ? "#89b4fa30" : "transparent"
                                border.width: 1

                                Row {
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.left: parent.left
                                    anchors.leftMargin: 10
                                    spacing: 8

                                    Rectangle {
                                        width: 7; height: 7; radius: 3.5
                                        anchors.verticalCenter: parent.verticalCenter
                                        color: fingerDialog.selectedFinger === modelData ? "#89b4fa" : "#1e2030"
                                        Behavior on color { ColorAnimation { duration: 150 } }
                                    }

                                    Text {
                                        text: modelData.replace(/-/g, " ").replace(/\b\w/g, function(c){ return c.toUpperCase() })
                                        color: fingerDialog.selectedFinger === modelData ? "#c8cfe8" : "#3d4158"
                                        font.pixelSize: 12
                                        font.letterSpacing: 0.2
                                        Behavior on color { ColorAnimation { duration: 150 } }
                                    }
                                }

                                MouseArea {
                                    id: rowHover
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: fingerDialog.selectedFinger = modelData
                                }
                            }
                        }
                    }
                }

                Item { width: 1; height: 4 }

                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 10

                    // Cancel
                    Rectangle {
                        width: 90; height: 36; radius: 18
                        color: cancelDlgMouse.containsMouse ? "#1a1a26" : "transparent"
                        border.color: "#1e2030"; border.width: 1
                        Text {
                            anchors.centerIn: parent
                            text: "Cancel"
                            color: "#353748"
                            font.pixelSize: 12
                        }
                        MouseArea {
                            id: cancelDlgMouse; anchors.fill: parent; hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: fingerDialog.visible = false
                        }
                    }

                    // Confirm
                    Rectangle {
                        width: 110; height: 36; radius: 18
                        color: fingerDialog.dialogMode === "delete"
                               ? (confirmDlgMouse.containsMouse ? "#1f0c0e" : "transparent")
                               : (confirmDlgMouse.containsMouse ? "#0f1828" : "transparent")
                        border.color: fingerDialog.dialogMode === "delete" ? "#f38ba840" : "#89b4fa40"
                        border.width: 1
                        Behavior on color { ColorAnimation { duration: 150 } }

                        Text {
                            anchors.centerIn: parent
                            text: fingerDialog.actionText
                            color: fingerDialog.dialogMode === "delete" ? "#f38ba8" : "#89b4fa"
                            font.pixelSize: 12
                            font.letterSpacing: 0.3
                        }
                        MouseArea {
                            id: confirmDlgMouse; anchors.fill: parent; hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (fingerDialog.dialogMode === "delete") {
                                    root.requestDelete(fingerDialog.selectedFinger)
                                } else if (fingerDialog.dialogMode === "verify") {
                                    overlay.reset()
                                    overlay.isEnrolling = false
                                    overlay.fingerName = fingerDialog.selectedFinger
                                        .replace(/-/g, " ")
                                        .replace(/\b\w/g, function(c){ return c.toUpperCase() })
                                    root.requestVerify(fingerDialog.selectedFinger)
                                    overlay.show()
                                    overlay.raise()
                                    overlay.requestActivate()
                                } else {
                                    overlay.reset()
                                    overlay.isEnrolling = true
                                    overlay.fingerName = fingerDialog.selectedFinger
                                        .replace(/-/g, " ")
                                        .replace(/\b\w/g, function(c){ return c.toUpperCase() })
                                    root.requestEnroll(fingerDialog.selectedFinger)
                                    overlay.show()
                                    overlay.raise()
                                    overlay.requestActivate()
                                }
                                fingerDialog.visible = false
                            }
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: root
        function onRequestEnroll(finger)  { fprintBridge.on_enroll(finger) }
        function onRequestVerify(finger)  { fprintBridge.on_verify(finger) }
        function onRequestStop()          { fprintBridge.on_stop() }
        function onRequestDelete(finger)  { fprintBridge.on_delete(finger) }
    }
}
