import QtQuick 2.15
import QtQuick.Controls 2.15

import QtQuick 2.15
import QtQuick.Controls 2.15

ApplicationWindow {
    id: window
    width: 1300
    height: 600
    visible: true
    title: "IPTables Log Monitor"

    Column {
        anchors.fill: parent
        spacing: 20
        Row{
            id: header
            spacing: 10
            Button {
                text: "Back to Page 1"
                onClicked: {
                    stackView.pop()
                    stackView.push(page1)
                }
            }
            Button {
                text: "Go to Page 2"
                onClicked: {
                    stackView.pop()
                    stackView.push(page2)
                }
            }

            Button {
                text: "Go to Page 3"
                onClicked: {
                    stackView.pop()
                    stackView.push(page3)
                }
            }

            Button {
                text: "Go to Page 4"
                onClicked: {
                    stackView.pop()
                    stackView.push(page4)
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
}
