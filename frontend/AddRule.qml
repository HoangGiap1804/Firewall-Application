import QtQuick 6.5
import QtQuick.Controls 6.5
Column {
        spacing: 10
        anchors.centerIn: parent

        TextField { id: ipField; width: 300; placeholderText: "Source IP (optional)" }
        TextField { id: portField; width: 300; placeholderText: "Port (optional)" }

        ComboBox { id: protocolBox; width: 300; model: ["tcp", "udp", "icmp"] }
        ComboBox { id: actionBox; width: 300; model: ["ACCEPT", "DROP", "REJECT"] }
        TextField { id: interfaceField; width: 300; placeholderText: "Interface (optional)" }
        TextField { id: stateField; width: 300; placeholderText: "State (NEW, ESTABLISHED) optional" }

        Button {
            text: "Add Rule"
            onClicked: {
                pyHandler.addRule(
                    ipField.text,
                    portField.text,
                    protocolBox.currentText,
                    actionBox.currentText,
                    interfaceField.text,
                    stateField.text
                )
            }
        }
    }