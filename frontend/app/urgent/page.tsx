import UrgentCard from "@/components/UrgentCard";

// Preview route for design review. The real app renders <UrgentCard /> from the check-in flow.
export default function UrgentPreview() {
  return <UrgentCard supportAlerted />;
}
