import QtQuick 2.15
import QtQuick.Controls 2.15

import "frontend"

ApplicationWindow {
    id: window
    width: 1300
    height: 600
    visible: true
    title: "IPTables Log Monitor"

    header: MenuBar {
        Menu {
            title: "File"
            MenuItem { text: "New" }
            MenuItem { text: "Open" }
            MenuSeparator {}
            MenuItem { text: "Save" }
            MenuItem { text: "Exit" }
        }
        Menu {
            title: "Edit"
            MenuItem { text: "Cut" }
            MenuItem { text: "Copy" }
            MenuItem { text: "Paste" }
        }
    }

    Column {
        anchors.fill: parent
        spacing: 20
        Row{
            id: header
            spacing: 10
            ButtonPage {
                text: "Back to Page 1"
                onClicked: {
                    stackView.pop()
                    stackView.push(page1)
                }
            }
            ButtonPage {
                text: "Go to Page 2"
                onClicked: {
                    stackView.pop()
                    stackView.push(page2)
                }
            }

            ButtonPage {
                text: "Go to Page 3"
                onClicked: {
                    stackView.pop()
                    stackView.push(page3)
                }
            }

            ButtonPage {
                text: "Go to Page 4"
                onClicked: {
                    stackView.pop()
                    stackView.push(page4)
                }
            }

            ButtonPage {
                text: "Go to Page 5"
                onClicked: {
                    stackView.pop()
                    stackView.push(page5)
                }
            }
            ButtonPage {
                text: "Firewall Controller"
                onClicked: {
                    stackView.pop()
                    stackView.push(page6)
                }
            }
            ButtonPage {
                text: "Available Rules"
                onClicked: {
                    stackView.pop()
                    stackView.push(page7)
                }
            }
        }
        StackView {
            id: stackView
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: header.bottom 
            anchors.bottom: parent.bottom
            initialItem: page1
        }
    }

    Component {
            id: page1
            Page {
                id: p1
                title: "Page 1"
                ShowPacket{}
            }
        }

    Component {
            id: page2
            Page {
                id: p2
                title: "Page 2"

                ShowInputRule{}
            }
        }

    Component {
            id: page3
            Page {
                id: p3
                title: "Page 3"

                AddRule{}
            }
        }

    Component {
            id: page4
            Page {
                id: p4
                title: "Page 4"

                AppNetwork{}
            }
        }

    Component {
            id: page5
            Page {
                id: p5
                title: "Page 5"

                Notification{}
            }
        }

    Component {
            id: page6
            Page {
                id: p6
                title: "Firewall Controller"

                FirewallController{}
            }
        }

    Component {
            id: page7
            Page {
                id: p7
                title: "Available Rules"

                AvailableRules{}
            }
        }
}
