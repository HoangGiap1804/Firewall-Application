import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    property string t: "NULL"
    radius: 10
    color: "#aecef3"
    border.color: "#0078d7"
    border.width: 1
    Text { anchors.centerIn: parent; text: t } 
}