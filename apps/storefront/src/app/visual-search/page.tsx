import { redirect } from "next/navigation";

/** Visual search lives in the global/product search bar now. */
export default function VisualSearchRedirectPage() {
  redirect("/products");
}
