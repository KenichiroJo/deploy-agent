import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

export interface ConfirmDialogModalProps {
  open: boolean;
  setOpen: (state: boolean) => void;
  onSuccess: () => void;
  onDiscard: () => void;
  chatName: string;
}

export const ConfirmDialogModal = ({
  open,
  setOpen,
  onSuccess,
  onDiscard,
  chatName,
}: ConfirmDialogModalProps) => {
  const handleXButton = () => {
    setOpen(false);
  };

  return (
    <Dialog defaultOpen={false} open={open} onOpenChange={handleXButton}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{'チャットを削除しますか？'}</DialogTitle>
        </DialogHeader>
        <DialogDescription>
          {'「'}{chatName}{'」を削除します。この操作は取り消せません。'}
        </DialogDescription>
        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => {
              onDiscard();
              setOpen(false);
            }}
          >
            {'キャンセル'}
          </Button>
          <Button
            variant="destructive"
            onClick={() => {
              onSuccess();
              setOpen(false);
            }}
          >
            {'削除'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
