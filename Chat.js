import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Centrifuge from 'centrifuge';

function Chat({ username, onLogout }) {
  const [users, setUsers] = useState([]);
  const [groups, setGroups] = useState([]);
  const [currentChat, setCurrentChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [messageText, setMessageText] = useState('');
  const [groupMembers, setGroupMembers] = useState([]);

  const centrifuge = new Centrifuge('ws://localhost:8000/connection/websocket');

  useEffect(() => {
    axios.get('http://localhost:5000/protected/users')
      .then(response => setUsers(response.data))
      .catch(error => console.error("Error fetching users:", error));

    axios.post('http://localhost:5000/protected/groups', { username })
      .then(response => setGroups(response.data))
      .catch(error => console.error("Error fetching groups:", error));

    centrifuge.subscribe(`user_${username}`, (message) => {
      setMessages((prevMessages) => [...prevMessages, message.data]);
    });

    centrifuge.connect();

    return () => {
      centrifuge.disconnect();
    };
  }, [username]);

  const selectChat = (userId) => {
    setCurrentChat({ type: 'user', id: userId });
    setMessages([]);
  };

  const createGroup = () => {
    const group_name = prompt("Enter group name:");
    if (!group_name || groupMembers.length === 0) return;

    const user_id = localStorage.getItem('user_id');
    axios.post('http://localhost:5000/protected/create_group', {
      group_name,
      member_ids: groupMembers.map(member => member.id),
      created_by: user_id,
    })
      .then(response => {
        const newGroup = { id: response.data.group_id, name: group_name };
        setGroups([...groups, newGroup]);

        centrifuge.subscribe(`group_${newGroup.id}`, (message) => {
          setMessages((prevMessages) => [...prevMessages, message.data]);
        });
      })
      .catch(error => console.error("Error creating group:", error));
  };

  const sendMessage = () => {
    const messagePayload = {
      sender_id: username,
      message: messageText
    };

    if (currentChat?.type === 'user') {
      messagePayload.recipient_id = currentChat.id;
    } else if (currentChat?.type === 'group') {
      messagePayload.group_id = currentChat.id;
    }

    axios.post('http://localhost:5000/protected/send', messagePayload)
      .then(() => setMessageText(''))
      .catch(error => console.error("Error sending message:", error));
  };

  return (
    <div>
      <h2>Chat</h2>

      <div>
        <h3>Users</h3>
        {users.map(user => (
          <button key={user.id} onClick={() => selectChat(user.id)}>
            Chat with {user.username}
          </button>
        ))}
      </div>

      <div>
        <h3>Groups</h3>
        {groups.map(group => (
          <button key={group.id} onClick={() => setCurrentChat({ type: 'group', id: group.id })}>
            {group.name}
          </button>
        ))}
        <button onClick={createGroup}>Create Group</button>
      </div>

      <div>
        <h3>Messages</h3>
        <div>
          {messages.map((msg, index) => (
            <div key={index}>
              <strong>{msg.username}:</strong> {msg.message}
            </div>
          ))}
        </div>
      </div>

      <textarea value={messageText} onChange={(e) => setMessageText(e.target.value)} placeholder="Type a message" />
      <button onClick={sendMessage}>Send</button>
    </div>
  );
}

export default Chat;
