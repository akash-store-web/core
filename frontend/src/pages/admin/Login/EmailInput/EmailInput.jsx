import React from 'react';
import './EmailInput.css';

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faEnvelope } from '@fortawesome/free-solid-svg-icons';

function EmailInput({placeholder}) {

  const [isValid, setIsValid] = React.useState(true);
  const [borderColor, setBorderColor] = React.useState('purple');
  const [email, setEmail] = React.useState('');

  const handleChange = (e) => {
    const newText = e.target.value;
    setEmail(newText);

    setIsValid((prevIsValid) => {
      const isValidEmail = validateEmail(newText);
      setBorderColor(isValidEmail ? 'green' : 'purple');
      return isValidEmail;
    });
    function validateEmail(email) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      return emailRegex.test(email);
    }}

    console.log(isValid);

  return (
    <div className="EmailInputRoot">
      <div className="EmailIcon">
        <FontAwesomeIcon icon={faEnvelope} />
      </div>
      <input className="EmailInputContainer" 
      type="email" 
      placeholder={placeholder}
      value={email}
      onChange={handleChange}
      style={{ borderColor: borderColor }}
      onBlur={() => {
        setBorderColor('purple');}}
       onFocus={() => {
        if (isValid) {
          setBorderColor('green');
        }}}
       
       />
       
    </div>
  );
}
export default EmailInput;