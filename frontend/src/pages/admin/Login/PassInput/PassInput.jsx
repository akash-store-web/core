import React from 'react';
import './PassInput.css';

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faLock, faEye, faEyeSlash } from '@fortawesome/free-solid-svg-icons';


function PassInput({placeholder}) {

      const [isVisible, setIsVisible] = React.useState(false);
    const inputRef = React.useRef(null);
    

function toggleClick() {
  setIsVisible((prevState) => !prevState);
  setTimeout(() => {
    if (inputRef.current) {
      inputRef.current.focus();
      const inputLength = inputRef.current.value.length;
      inputRef.current.setSelectionRange(inputLength, inputLength);
    }
  }, 0);
}

  return(
    <div className="PassInputRoot">
      <div className="PassIcon">
        <FontAwesomeIcon icon={faLock} />
      </div>
      <input 
      ref={inputRef}
      className="PassInputContainer" 
      type={isVisible ? "text" : "password"} 
      placeholder={placeholder}
       />
       <div className="eyeIcon" onClick={toggleClick}>
        <FontAwesomeIcon icon={isVisible ? faEyeSlash : faEye} />
      </div>
    </div>
  );
}
export default PassInput;