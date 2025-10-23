import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Page {
    id: root
    title: "Available Rules"

    property var rulesStatus: ({})

    ColumnLayout {
        anchors.fill: parent
        spacing: 10
        anchors.margins: 20

        Text {
            text: "                Available Rules                 "
            font.bold: true
            font.pixelSize: 22
            Layout.alignment: Qt.AlignHCenter
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ListView {
                id: rulesList
                clip: true
                spacing: 10
                width: parent.width
                model: Object.keys(rulesStatus)

                delegate: Rectangle {
                    width: parent.width - 30
                    height: 60
                    radius: 10
                    color: "#f9f9f9"
                    border.width: 1
                    border.color: "#bfbfbf"

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 20

                        Text {
                            text: modelData
                            font.pixelSize: 18
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter
                        }

                        Switch {
                            id: toggle
                            checked: rulesStatus[modelData].enabled
                            Layout.alignment: Qt.AlignVCenter
                            onToggled: {
                                var result = availableRules.toggleRule(modelData, checked)
                                console.log(result)
                                try {
                                    notification.showMessage(modelData + (checked ? " enabled" : " disabled"))
                                } catch(e) {
                                    console.log("Notification unavailable:", e)
                                }
                                rulesStatus[modelData].enabled = checked
                                rulesList.model = Object.keys(rulesStatus)
                            }
                        }
                    }
                }
            }
        }
    }

    Component.onCompleted: {
        rulesStatus = availableRules.getStatus()
        rulesList.model = Object.keys(rulesStatus)
    }

    Connections {
        target: availableRules
        onRuleToggled: function(ruleName, enabled) {
            rulesStatus[ruleName].enabled = enabled
            rulesList.model = Object.keys(rulesStatus)
        }
    }
}
