import "./StatusMessage.css";

type StatusMessageProps = {
    type: "loading" | "error" | "empty";
    title: string;
    message: string;
};

function StatusMessage({
    type,
    title,
    message,
}: StatusMessageProps) {
    return (
        <div
            className={`status-message status-message-${type}`}
            role={type === "error" ? "alert" : "status"}
        >
            <strong>{title}</strong>
            <p>{message}</p>
        </div>
    );
}

export default StatusMessage;