import React from 'react';
import './EmailInput.css';

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faEnvelope } from '@fortawesome/free-solid-svg-icons';

function EmailInput({placeholder}) {
  return (
    <div className="EmailInputRoot">
      <div className="EmailIcon">
        <FontAwesomeIcon icon={faEnvelope} />
      </div>
      <input className="EmailInputContainer" 
      type="email" 
      placeholder={placeholder}
       />
       ;
    </div>
  );
}
export default EmailInput;