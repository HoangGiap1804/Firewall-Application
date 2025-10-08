import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        Text { text: "Iptables Mitigation Control"; font.pixelSize: 20 }

        GridLayout {
            columns: 2
            columnSpacing: 12
            rowSpacing: 8
            Layout.fillWidth: true

            // Row for each ruleset
            function mkRow(labelText, callback) {
                var row = Qt.createQmlObject('import QtQuick; import QtQuick.Controls; Row { spacing: 8 }', parent)
                return row
            }

            // SYN flood
            Row {
                spacing: 8
                Button {
                    text: "Apply SYN-rate rules"
                    onClicked: {
                        statusText.text = firewall.apply_rule_set("syn_flood")
                    }
                }
                Button {
                    text: "Flush MYFW"
                    onClicked: {
                        statusText.text = firewall.flush_myfw()
                    }
                }
            }

            // ICMP limit
            Row {
                spacing: 8
                Button {
                    text: "Apply ICMP limit"
                    onClicked: statusText.text = firewall.apply_rule_set("icmp_limit")
                }
                Button {
                    text: "Apply SSH rate"
                    onClicked: statusText.text = firewall.apply_rule_set("ssh_rate")
                }
            }

            Row {
                spacing: 8
                Button {
                    text: "Apply NULL/XMAS drop"
                    onClicked: statusText.text = firewall.apply_rule_set("null_xmas")
                }
                Button {
                    text: "Block spoofed private src"
                    onClicked: statusText.text = firewall.apply_rule_set("spoof_block")
                }
            }

            Row {
                spacing: 8
                Button {
                    text: "Apply ALL"
                    onClicked: statusText.text = firewall.apply_all()
                }
                Button {
                    text: "Delete chain MYFW"
                    onClicked: statusText.text = firewall.delete_myfw_chain()
                }
            }

            Row {
                spacing: 8
                Button {
                    text: "Show status"
                    onClicked: statusText.text = firewall.status()
                }
                Button {
                    text: "Flush then Show"
                    onClicked: {
                        var r = firewall.flush_myfw()
                        statusText.text = r + "\n\n" + firewall.status()
                    }
                }
            }
        }

        TextArea {
            id: statusText
            Layout.fillWidth: true
            Layout.fillHeight: true
            font.family: "monospace"
            readOnly: true
            wrapMode: TextArea.NoWrap
            text: "Ready. Tip: run this program as root (sudo)."
        }

        Row {
            spacing: 8
            Button {
                text: "Quit"
                onClicked: Qt.quit()
            }
            Label {
                text: "WAN interface: " + (typeof Qt === "object" ? "" : "")
                // Note: WAN_IFACE is defined in Python. Edit main.py to change WAN_IFACE.
            }
        }
    }
