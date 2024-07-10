import { TextareaAutosize as BaseTextareaAutosize } from "@mui/base/TextareaAutosize";
import { styled } from "@mui/system";

export default function UnstyledTextareaIntroduction({ value, onChange, placeholder }) {
  return (
    <TextareaAutosize
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      aria-label="empty textarea"
    />
  );
}

const TextareaAutosize = styled(BaseTextareaAutosize)(
  () => `
    font-family: 'Roboto', 'Open Sans', 'Lato', sans-serif;
    font-size: 13px;
    border-radius: 17px;
    resize: none;
    width: 100%;
    padding: 10px;
    border: none;
    color: white;
    background-color: #3C3C43;
    line-height: 1.1rem;

    &:focus {
        border: none;
        outline: none;
    }

    // firefox
    &:focus-visible {
        border: none;
        outline: none;
    }
`,
);
